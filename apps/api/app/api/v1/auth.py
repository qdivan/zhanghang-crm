from datetime import datetime
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.security import create_access_token, verify_password
from app.db.session import get_db
from app.models import User
from app.schemas.auth import (
    AuthProvidersOut,
    SsoExchangeRequest,
    SsoExchangeResponse,
    TokenResponse,
    UserOut,
)
from app.services.audit import write_operation_log
from app.services.data_access import has_module_read_grant
from app.services.login_security import (
    clear_local_login_failures,
    ensure_local_login_ip_allowed,
    register_local_login_failure,
)
from app.services.soft_delete import active_filter
from app.services.sso import (
    PENDING_BINDING_MESSAGE,
    SsoConflictError,
    SsoError,
    build_auth_provider_payload,
    build_sso_logout_url,
    build_sso_login_url,
    consume_exchange_ticket,
    create_exchange_ticket,
    create_sso_state_ticket,
    exchange_code_for_tokens,
    get_valid_state_ticket,
    resolve_or_create_local_user,
    sso_is_enabled,
    verify_id_token,
)

from app.schemas.auth import LoginRequest

router = APIRouter(prefix="/auth", tags=["auth"])


def build_user_out(db: Session, user: User) -> UserOut:
    granted_modules: list[str] = []
    if user.role == "ACCOUNTANT":
        for module in ["CUSTOMER", "BILLING"]:
            if has_module_read_grant(db, user.id, module):
                granted_modules.append(module)
    return UserOut.model_validate(
        {
            **user.__dict__,
            "email": user.email or "",
            "display_name": user.display_name or "",
            "external_managed": bool(user.external_managed),
            "sso_bound": len(user.identities) > 0,
            "granted_read_modules": granted_modules,
        }
    )


def _issue_token_response(db: Session, user: User) -> TokenResponse:
    token = create_access_token(subject=user.username, role=user.role, user_id=user.id)
    return TokenResponse(access_token=token, user=build_user_out(db, user))


def _create_frontend_exchange_redirect(ticket_value: str) -> RedirectResponse:
    query = urlencode({"ticket": ticket_value})
    return RedirectResponse(url=f"{settings.oidc_frontend_exchange_url}?{query}", status_code=status.HTTP_302_FOUND)


def _local_login_restricted(user: User) -> bool:
    if settings.local_login_enabled:
        return False
    return not (user.auth_source == "LOCAL" and user.role in {"OWNER", "ADMIN"})


@router.get("/providers", response_model=AuthProvidersOut)
def get_auth_providers():
    return AuthProvidersOut.model_validate(build_auth_provider_payload())


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = db.execute(select(User).where(User.username == payload.username, active_filter(User))).scalar_one_or_none()
    ip_address, security_setting = ensure_local_login_ip_allowed(db, request=request, user=user)

    if user is None or not user.is_active:
        should_track_local_failure = user is None or user.auth_source == "LOCAL"
        if should_track_local_failure and register_local_login_failure(
            db,
            ip_address=ip_address,
            username=payload.username,
            setting=security_setting,
        ):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"该IP登录失败次数过多，已锁定 {security_setting.local_ip_lock_window_minutes} 分钟，请稍后再试",
            )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号或密码错误")

    if _local_login_restricted(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="当前环境已关闭普通账号本地登录，请使用企业单点登录",
        )

    if not verify_password(payload.password, user.password_hash):
        if user.auth_source == "LOCAL" and register_local_login_failure(
            db,
            ip_address=ip_address,
            username=payload.username,
            setting=security_setting,
        ):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"该IP登录失败次数过多，已锁定 {security_setting.local_ip_lock_window_minutes} 分钟，请稍后再试",
            )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号或密码错误")

    if user.auth_source == "LOCAL":
        clear_local_login_failures(db, ip_address=ip_address)

    user.last_login_at = datetime.utcnow()
    write_operation_log(
        db,
        actor_id=user.id,
        action="LOGIN",
        entity_type="USER",
        entity_id=user.id,
        detail=f"username={user.username},ip={ip_address},method=local",
    )
    db.commit()
    db.refresh(user)
    return _issue_token_response(db, user)


@router.get("/sso/login")
def sso_login(db: Session = Depends(get_db)):
    if not sso_is_enabled():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="企业单点登录未启用")
    ticket = create_sso_state_ticket(db)
    return RedirectResponse(url=build_sso_login_url(ticket), status_code=status.HTTP_302_FOUND)


@router.get("/sso/callback")
def sso_callback(
    state: str = "",
    code: str = "",
    error: str = "",
    error_description: str = "",
    db: Session = Depends(get_db),
):
    if not sso_is_enabled():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="企业单点登录未启用")

    if error:
        exchange_ticket = create_exchange_ticket(
            db,
            status="ERROR",
            error_code=error,
            error_message=error_description or "企业单点登录未完成",
        )
        return _create_frontend_exchange_redirect(exchange_ticket.ticket)

    try:
        state_ticket = get_valid_state_ticket(db, state)
    except SsoError as exc:
        exchange_ticket = create_exchange_ticket(
            db,
            status="ERROR",
            error_code="STATE_INVALID",
            error_message=str(exc),
        )
        return _create_frontend_exchange_redirect(exchange_ticket.ticket)

    try:
        token_payload = exchange_code_for_tokens(code)
        id_token = str(token_payload.get("id_token") or "").strip()
        access_token = str(token_payload.get("access_token") or "").strip()
        if not id_token:
            raise SsoError("企业单点登录未返回身份令牌")
        claims = verify_id_token(id_token, nonce=state_ticket.nonce, access_token=access_token)
        user, outcome = resolve_or_create_local_user(db, claims)
        user.last_login_at = datetime.utcnow()
        write_operation_log(
            db,
            actor_id=user.id,
            action="SSO_LOGIN",
            entity_type="USER",
            entity_id=user.id,
            detail=f"outcome={outcome},issuer={claims.get('iss', '')}",
        )
        db.commit()
        exchange_ticket = create_exchange_ticket(db, status="READY", user_id=user.id)
    except SsoConflictError as exc:
        exchange_ticket = create_exchange_ticket(
            db,
            status="CONFLICT",
            conflict_id=exc.conflict.id,
            error_code="PENDING_BINDING",
            error_message=PENDING_BINDING_MESSAGE,
        )
    except SsoError as exc:
        exchange_ticket = create_exchange_ticket(
            db,
            status="ERROR",
            error_code="SSO_FAILED",
            error_message=str(exc),
        )

    state_ticket.status = "DONE"
    state_ticket.consumed_at = datetime.utcnow()
    db.commit()
    return _create_frontend_exchange_redirect(exchange_ticket.ticket)


@router.post("/sso/exchange", response_model=SsoExchangeResponse)
def exchange_sso_ticket(payload: SsoExchangeRequest, db: Session = Depends(get_db)):
    try:
        ticket = consume_exchange_ticket(db, payload.ticket.strip())
    except SsoError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if ticket.status == "READY" and ticket.user_id:
        user = db.execute(select(User).where(User.id == ticket.user_id, active_filter(User))).scalar_one_or_none()
        if user is None or not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号不存在或已停用")
        token_response = _issue_token_response(db, user)
        return SsoExchangeResponse(
            status="SUCCESS",
            message="企业单点登录成功",
            access_token=token_response.access_token,
            token_type=token_response.token_type,
            user=token_response.user,
            provider_label=settings.sso_provider_label,
        )
    if ticket.status == "CONFLICT":
        return SsoExchangeResponse(
            status="PENDING_BINDING",
            message=ticket.error_message or PENDING_BINDING_MESSAGE,
            conflict_id=ticket.conflict_id,
            provider_label=settings.sso_provider_label,
        )
    return SsoExchangeResponse(
        status="ERROR",
        message=ticket.error_message or "企业单点登录失败，请稍后重试",
        provider_label=settings.sso_provider_label,
    )


@router.post("/sso/logout")
def sso_logout():
    try:
        logout_url = build_sso_logout_url()
    except SsoError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return {"logout_url": logout_url}


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return build_user_out(db, current_user)
