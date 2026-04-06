from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.security import create_access_token, verify_password
from app.db.session import get_db
from app.models import User
from app.schemas.auth import LoginRequest, TokenResponse, UserOut
from app.services.audit import write_operation_log
from app.services.data_access import has_module_read_grant
from app.services.login_security import (
    clear_local_login_failures,
    ensure_local_login_ip_allowed,
    register_local_login_failure,
)
from app.services.soft_delete import active_filter

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
            "granted_read_modules": granted_modules,
        }
    )


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
        detail=f"username={user.username},ip={ip_address}",
    )
    db.commit()

    token = create_access_token(subject=user.username, role=user.role)
    return TokenResponse(access_token=token, user=build_user_out(db, user))


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return build_user_out(db, current_user)
