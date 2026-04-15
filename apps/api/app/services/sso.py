from __future__ import annotations

import json
import logging
import secrets
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Any, Optional
from urllib.parse import urlencode

import httpx
from jose import JWTError, jwt
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.models import SsoBindingConflict, SsoLoginTicket, User, UserIdentity
from app.services.soft_delete import active_filter

PROVIDER_KEYCLOAK = "keycloak"
DEFAULT_SSO_ROLE = "ACCOUNTANT"
PENDING_BINDING_MESSAGE = "当前企业账号需要管理员在后台确认绑定后才能进入 CRM。"
logger = logging.getLogger(__name__)
GROUP_ROLE_MAP = {
    "crm-owner": "OWNER",
    "crm-admin": "ADMIN",
    "crm-manager": "MANAGER",
    "crm-accountant": "ACCOUNTANT",
}


class SsoError(Exception):
    pass


class SsoConfigError(SsoError):
    pass


class SsoConflictError(SsoError):
    def __init__(self, conflict: SsoBindingConflict):
        super().__init__(PENDING_BINDING_MESSAGE)
        self.conflict = conflict


def sso_is_enabled() -> bool:
    return settings.sso_ready


def build_auth_provider_payload() -> dict[str, Any]:
    return {
        "local": {
            "enabled": True,
            "admin_only": not settings.local_login_enabled,
            "label": "本地账号登录",
        },
        "sso": {
            "enabled": sso_is_enabled(),
            "label": settings.sso_provider_label,
        },
    }


def _normalize_claim_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_username_candidate(*candidates: Any) -> str:
    for candidate in candidates:
        raw = _normalize_claim_text(candidate)
        if raw:
            return raw
    return ""


def _build_random_password() -> str:
    return hash_password(secrets.token_urlsafe(24))


def _display_name_from_claims(claims: dict[str, Any]) -> str:
    for key in ("name", "display_name", "given_name", "preferred_username", "email"):
        value = _normalize_claim_text(claims.get(key))
        if value:
            return value
    return "SSO用户"


def _extract_groups(claims: dict[str, Any]) -> list[str]:
    normalized: list[str] = []
    raw_groups = claims.get("groups")
    if isinstance(raw_groups, list):
        normalized.extend(_normalize_claim_text(item).lstrip("/") for item in raw_groups if _normalize_claim_text(item))
    realm_access = claims.get("realm_access")
    if isinstance(realm_access, dict):
        roles = realm_access.get("roles")
        if isinstance(roles, list):
            normalized.extend(_normalize_claim_text(item).lstrip("/") for item in roles if _normalize_claim_text(item))
    seen: set[str] = set()
    result: list[str] = []
    for item in normalized:
        token = item.strip()
        if token and token not in seen:
            seen.add(token)
            result.append(token)
    return result


def infer_role_from_claims(claims: dict[str, Any]) -> str:
    for group in _extract_groups(claims):
        mapped = GROUP_ROLE_MAP.get(group)
        if mapped:
            return mapped
    return DEFAULT_SSO_ROLE


def _discovery_cache_key() -> tuple[str, str]:
    return (settings.oidc_issuer.strip(), settings.oidc_client_id.strip())


@lru_cache(maxsize=4)
def _load_discovery_cached(cache_key: tuple[str, str]) -> dict[str, Any]:
    issuer, _client_id = cache_key
    discovery_url = f"{issuer.rstrip('/')}/.well-known/openid-configuration"
    with httpx.Client(timeout=10.0, follow_redirects=True) as client:
        response = client.get(discovery_url)
        response.raise_for_status()
        return response.json()


def get_oidc_discovery() -> dict[str, Any]:
    if not sso_is_enabled():
        raise SsoConfigError("SSO 尚未启用或配置不完整")
    return _load_discovery_cached(_discovery_cache_key())


@lru_cache(maxsize=4)
def _load_jwks_cached(jwks_uri: str) -> dict[str, Any]:
    with httpx.Client(timeout=10.0, follow_redirects=True) as client:
        response = client.get(jwks_uri)
        response.raise_for_status()
        return response.json()


def _load_jwks() -> dict[str, Any]:
    discovery = get_oidc_discovery()
    jwks_uri = _normalize_claim_text(discovery.get("jwks_uri"))
    if not jwks_uri:
        raise SsoConfigError("OIDC Discovery 未返回 jwks_uri")
    return _load_jwks_cached(jwks_uri)


def create_sso_state_ticket(db: Session) -> SsoLoginTicket:
    now = datetime.utcnow()
    ticket = SsoLoginTicket(
        ticket=secrets.token_urlsafe(32),
        provider=PROVIDER_KEYCLOAK,
        purpose="STATE",
        status="PENDING",
        nonce=secrets.token_urlsafe(24),
        expires_at=now + timedelta(minutes=settings.sso_flow_ttl_minutes),
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


def build_sso_login_url(ticket: SsoLoginTicket) -> str:
    discovery = get_oidc_discovery()
    authorization_endpoint = _normalize_claim_text(discovery.get("authorization_endpoint"))
    if not authorization_endpoint:
        raise SsoConfigError("OIDC Discovery 未返回 authorization_endpoint")
    query = urlencode(
        {
            "response_type": "code",
            "client_id": settings.oidc_client_id.strip(),
            "redirect_uri": settings.oidc_callback_url,
            "scope": " ".join(settings.oidc_scope_list),
            "state": ticket.ticket,
            "nonce": ticket.nonce,
        }
    )
    return f"{authorization_endpoint}?{query}"


def get_valid_state_ticket(db: Session, state: str) -> SsoLoginTicket:
    ticket = db.execute(
        select(SsoLoginTicket).where(
            SsoLoginTicket.ticket == state,
            SsoLoginTicket.purpose == "STATE",
        )
    ).scalar_one_or_none()
    if ticket is None or ticket.consumed_at is not None:
        raise SsoError("登录状态已失效，请重新发起企业单点登录")
    if ticket.expires_at < datetime.utcnow():
        raise SsoError("企业单点登录已过期，请重新发起登录")
    return ticket


def create_exchange_ticket(
    db: Session,
    *,
    status: str,
    user_id: Optional[int] = None,
    conflict_id: Optional[int] = None,
    error_code: str = "",
    error_message: str = "",
) -> SsoLoginTicket:
    ticket = SsoLoginTicket(
        ticket=secrets.token_urlsafe(32),
        provider=PROVIDER_KEYCLOAK,
        purpose="EXCHANGE",
        status=status,
        user_id=user_id,
        conflict_id=conflict_id,
        error_code=error_code,
        error_message=error_message,
        expires_at=datetime.utcnow() + timedelta(minutes=settings.sso_exchange_ttl_minutes),
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


def consume_exchange_ticket(db: Session, ticket_value: str) -> SsoLoginTicket:
    ticket = db.execute(
        select(SsoLoginTicket).where(
            SsoLoginTicket.ticket == ticket_value,
            SsoLoginTicket.purpose == "EXCHANGE",
        )
    ).scalar_one_or_none()
    if ticket is None or ticket.consumed_at is not None:
        raise SsoError("登录票据已失效，请重新发起企业单点登录")
    if ticket.expires_at < datetime.utcnow():
        raise SsoError("登录票据已过期，请重新发起企业单点登录")
    ticket.consumed_at = datetime.utcnow()
    db.commit()
    db.refresh(ticket)
    return ticket


def exchange_code_for_tokens(code: str) -> dict[str, Any]:
    discovery = get_oidc_discovery()
    token_endpoint = _normalize_claim_text(discovery.get("token_endpoint"))
    if not token_endpoint:
        raise SsoConfigError("OIDC Discovery 未返回 token_endpoint")
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.oidc_callback_url,
        "client_id": settings.oidc_client_id.strip(),
        "client_secret": settings.oidc_client_secret.strip(),
    }
    with httpx.Client(timeout=10.0, follow_redirects=True) as client:
        response = client.post(token_endpoint, data=payload)
        if response.status_code >= 400:
            raise SsoError("企业单点登录换取令牌失败")
        return response.json()


def verify_id_token(id_token: str, *, nonce: str, access_token: str = "") -> dict[str, Any]:
    header = jwt.get_unverified_header(id_token)
    kid = _normalize_claim_text(header.get("kid"))
    alg = _normalize_claim_text(header.get("alg")) or "RS256"
    jwks = _load_jwks()
    key = next((item for item in jwks.get("keys", []) if _normalize_claim_text(item.get("kid")) == kid), None)
    if key is None:
        raise SsoError("企业单点登录签名校验失败")
    try:
        claims = jwt.decode(
            id_token,
            key,
            algorithms=[alg],
            audience=settings.oidc_client_id.strip(),
            issuer=settings.oidc_issuer.strip(),
            access_token=access_token or None,
        )
    except JWTError as exc:
        logger.warning(
            "OIDC id_token verification failed: kid=%s alg=%s issuer=%s audience=%s error=%s",
            kid,
            alg,
            settings.oidc_issuer.strip(),
            settings.oidc_client_id.strip(),
            str(exc),
        )
        raise SsoError("企业单点登录令牌校验失败") from exc
    if _normalize_claim_text(claims.get("nonce")) != nonce:
        raise SsoError("企业单点登录状态校验失败，请重新登录")
    return claims


def _existing_identity(
    db: Session,
    *,
    issuer: str,
    subject: str,
) -> Optional[UserIdentity]:
    return db.execute(
        select(UserIdentity).where(
            UserIdentity.provider == PROVIDER_KEYCLOAK,
            UserIdentity.issuer == issuer,
            UserIdentity.subject == subject,
        )
    ).scalar_one_or_none()


def _candidate_users(db: Session, *, email: str, username: str) -> list[User]:
    clauses = []
    if email:
        clauses.append(func.lower(User.email) == email.lower())
    if username:
        clauses.append(func.lower(User.username) == username.lower())
    if not clauses:
        return []
    stmt = select(User).where(active_filter(User), or_(*clauses))
    return list(db.execute(stmt).scalars().all())


def _update_user_projection(user: User, claims: dict[str, Any]) -> None:
    email = _normalize_claim_text(claims.get("email"))
    display_name = _display_name_from_claims(claims)
    if not user.external_managed:
        user.external_managed = True
    if email and user.email != email:
        user.email = email
    if display_name and user.display_name != display_name:
        user.display_name = display_name


def _sync_identity(identity: UserIdentity, claims: dict[str, Any]) -> None:
    identity.preferred_username = _normalize_username_candidate(
        claims.get("preferred_username"),
        claims.get("preferred_username".upper()),
    )
    identity.email = _normalize_claim_text(claims.get("email"))
    identity.email_verified = bool(claims.get("email_verified"))
    identity.display_name = _display_name_from_claims(claims)
    identity.raw_claims_json = json.dumps(claims, ensure_ascii=False)
    identity.last_login_at = datetime.utcnow()


def _ensure_unique_username(db: Session, preferred_username: str, email: str, display_name: str) -> str:
    base = _normalize_username_candidate(preferred_username, email.split("@")[0] if email else "", display_name, "sso-user")
    normalized = base.replace(" ", "-").replace("/", "-")
    normalized = "".join(ch for ch in normalized if ch.isalnum() or ch in {"-", "_", "."}) or "sso-user"
    candidate = normalized[:64]
    suffix = 1
    while db.execute(select(User).where(User.username == candidate)).scalar_one_or_none() is not None:
        suffix_text = f"-{suffix}"
        candidate = f"{normalized[: max(1, 64 - len(suffix_text))]}{suffix_text}"
        suffix += 1
    return candidate


def _upsert_conflict(
    db: Session,
    *,
    issuer: str,
    subject: str,
    claims: dict[str, Any],
    reason: str,
    candidate_users: list[User],
) -> SsoBindingConflict:
    conflict = db.execute(
        select(SsoBindingConflict).where(
            SsoBindingConflict.provider == PROVIDER_KEYCLOAK,
            SsoBindingConflict.issuer == issuer,
            SsoBindingConflict.subject == subject,
            SsoBindingConflict.status == "PENDING",
        )
    ).scalar_one_or_none()
    now = datetime.utcnow()
    candidate_user_ids = [item.id for item in candidate_users]
    if conflict is None:
        conflict = SsoBindingConflict(
            provider=PROVIDER_KEYCLOAK,
            issuer=issuer,
            subject=subject,
            preferred_username=_normalize_username_candidate(claims.get("preferred_username")),
            email=_normalize_claim_text(claims.get("email")),
            display_name=_display_name_from_claims(claims),
            raw_claims_json=json.dumps(claims, ensure_ascii=False),
            reason=reason,
            status="PENDING",
            candidate_user_ids_json=json.dumps(candidate_user_ids),
            first_seen_at=now,
            last_seen_at=now,
        )
        db.add(conflict)
    else:
        conflict.preferred_username = _normalize_username_candidate(claims.get("preferred_username"))
        conflict.email = _normalize_claim_text(claims.get("email"))
        conflict.display_name = _display_name_from_claims(claims)
        conflict.raw_claims_json = json.dumps(claims, ensure_ascii=False)
        conflict.reason = reason
        conflict.candidate_user_ids_json = json.dumps(candidate_user_ids)
        conflict.last_seen_at = now
    db.commit()
    db.refresh(conflict)
    return conflict


def resolve_or_create_local_user(db: Session, claims: dict[str, Any]) -> tuple[User, str]:
    issuer = _normalize_claim_text(claims.get("iss"))
    subject = _normalize_claim_text(claims.get("sub"))
    if not issuer or not subject:
        raise SsoError("企业单点登录身份信息不完整")

    identity = _existing_identity(db, issuer=issuer, subject=subject)
    if identity is not None:
        user = identity.user
        if user is None or user.is_deleted or not user.is_active:
            raise SsoError("当前企业账号在 CRM 中已停用，请联系管理员")
        _update_user_projection(user, claims)
        _sync_identity(identity, claims)
        db.commit()
        db.refresh(user)
        return user, "BOUND"

    email = _normalize_claim_text(claims.get("email"))
    preferred_username = _normalize_username_candidate(claims.get("preferred_username"), claims.get("preferred_username".upper()))
    unique_email_matches = []
    if email:
        unique_email_matches = list(
            db.execute(
                select(User).where(active_filter(User), func.lower(User.email) == email.lower())
            ).scalars().all()
        )
    if len(unique_email_matches) == 1:
        user = unique_email_matches[0]
        _update_user_projection(user, claims)
        identity = UserIdentity(user_id=user.id)
        _sync_identity(identity, claims)
        identity.issuer = issuer
        identity.subject = subject
        db.add(identity)
        db.commit()
        db.refresh(user)
        return user, "AUTO_BOUND_EMAIL"
    if len(unique_email_matches) > 1:
        conflict = _upsert_conflict(
            db,
            issuer=issuer,
            subject=subject,
            claims=claims,
            reason="邮箱匹配到多个本地账号",
            candidate_users=unique_email_matches,
        )
        raise SsoConflictError(conflict)

    unique_username_matches = []
    if preferred_username:
        unique_username_matches = list(
            db.execute(
                select(User).where(active_filter(User), func.lower(User.username) == preferred_username.lower())
            ).scalars().all()
        )
    if len(unique_username_matches) == 1:
        user = unique_username_matches[0]
        _update_user_projection(user, claims)
        identity = UserIdentity(user_id=user.id)
        _sync_identity(identity, claims)
        identity.issuer = issuer
        identity.subject = subject
        db.add(identity)
        db.commit()
        db.refresh(user)
        return user, "AUTO_BOUND_USERNAME"
    if len(unique_username_matches) > 1:
        conflict = _upsert_conflict(
            db,
            issuer=issuer,
            subject=subject,
            claims=claims,
            reason="用户名匹配到多个本地账号",
            candidate_users=unique_username_matches,
        )
        raise SsoConflictError(conflict)

    username = _ensure_unique_username(db, preferred_username, email, _display_name_from_claims(claims))
    user = User(
        username=username,
        password_hash=_build_random_password(),
        auth_source="SSO",
        email=email,
        display_name=_display_name_from_claims(claims),
        external_managed=True,
        role=infer_role_from_claims(claims),
        is_active=True,
    )
    db.add(user)
    db.flush()
    identity = UserIdentity(
        user_id=user.id,
        provider=PROVIDER_KEYCLOAK,
        issuer=issuer,
        subject=subject,
    )
    _sync_identity(identity, claims)
    db.add(identity)
    db.commit()
    db.refresh(user)
    return user, "AUTO_CREATED"


def create_manual_binding(
    db: Session,
    *,
    user: User,
    issuer: str,
    subject: str,
    preferred_username: str = "",
    email: str = "",
    email_verified: bool = False,
    display_name: str = "",
    raw_claims_json: str = "",
) -> UserIdentity:
    existing_for_user = db.execute(
        select(UserIdentity).where(
            UserIdentity.user_id == user.id,
            UserIdentity.provider == PROVIDER_KEYCLOAK,
        )
    ).scalar_one_or_none()
    if existing_for_user is not None:
        raise SsoError("该本地用户已绑定企业单点登录")

    existing_identity = _existing_identity(db, issuer=issuer, subject=subject)
    if existing_identity is not None:
        raise SsoError("该企业身份已绑定其他本地账号")

    identity = UserIdentity(
        user_id=user.id,
        provider=PROVIDER_KEYCLOAK,
        issuer=issuer,
        subject=subject,
        preferred_username=preferred_username,
        email=email,
        email_verified=email_verified,
        display_name=display_name,
        raw_claims_json=raw_claims_json,
        last_login_at=None,
    )
    db.add(identity)
    user.external_managed = True
    if email and not user.email:
        user.email = email
    if display_name and not user.display_name:
        user.display_name = display_name
    db.commit()
    db.refresh(identity)
    return identity
