import math
from datetime import datetime, timedelta
from typing import Optional

from fastapi import HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import LoginIpLock, SecuritySetting, User
from app.services.audit import write_operation_log

DEFAULT_LOCK_WINDOW_MINUTES = 5
DEFAULT_LOCK_MAX_ATTEMPTS = 20


def get_or_create_security_setting(db: Session) -> SecuritySetting:
    setting = db.execute(select(SecuritySetting).limit(1)).scalar_one_or_none()
    if setting is not None:
        return setting

    setting = SecuritySetting(
        local_ip_lock_enabled=True,
        local_ip_lock_window_minutes=DEFAULT_LOCK_WINDOW_MINUTES,
        local_ip_lock_max_attempts=DEFAULT_LOCK_MAX_ATTEMPTS,
    )
    db.add(setting)
    db.commit()
    db.refresh(setting)
    return setting


def get_request_ip(request: Request) -> str:
    forwarded_for = (request.headers.get("x-forwarded-for") or "").strip()
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()[:64]

    real_ip = (request.headers.get("x-real-ip") or "").strip()
    if real_ip:
        return real_ip[:64]

    client_host = request.client.host if request.client else ""
    return (client_host or "unknown")[:64]


def _get_ip_lock(db: Session, ip_address: str) -> Optional[LoginIpLock]:
    return db.execute(select(LoginIpLock).where(LoginIpLock.ip_address == ip_address)).scalar_one_or_none()


def ensure_local_login_ip_allowed(
    db: Session,
    *,
    request: Request,
    user: Optional[User],
) -> tuple[str, SecuritySetting]:
    target_auth_source = user.auth_source if user is not None else "LOCAL"
    ip_address = get_request_ip(request)
    setting = get_or_create_security_setting(db)

    if target_auth_source != "LOCAL" or not setting.local_ip_lock_enabled:
        return ip_address, setting

    lock = _get_ip_lock(db, ip_address)
    now = datetime.utcnow()
    if lock is not None and lock.blocked_until is not None and lock.blocked_until > now:
        remaining_minutes = max(1, math.ceil((lock.blocked_until - now).total_seconds() / 60))
        write_operation_log(
            db,
            actor_id=user.id if user is not None else None,
            action="LOGIN_IP_BLOCKED",
            entity_type="SECURITY",
            entity_id=ip_address,
            detail=f"ip={ip_address},remaining_minutes={remaining_minutes},last_username={lock.last_username}",
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"该IP登录失败次数过多，已锁定 {remaining_minutes} 分钟，请稍后再试",
        )

    if lock is not None and lock.blocked_until is not None and lock.blocked_until <= now:
        db.delete(lock)
        db.commit()

    return ip_address, setting


def register_local_login_failure(
    db: Session,
    *,
    ip_address: str,
    username: str,
    setting: SecuritySetting,
) -> bool:
    if not setting.local_ip_lock_enabled:
        return False

    now = datetime.utcnow()
    lock = _get_ip_lock(db, ip_address)
    window_delta = timedelta(minutes=max(int(setting.local_ip_lock_window_minutes or 0), 1))

    if lock is None:
        lock = LoginIpLock(
            ip_address=ip_address,
            failed_count=1,
            first_failed_at=now,
            last_failed_at=now,
            last_username=username[:64],
        )
        db.add(lock)
    else:
        if lock.first_failed_at is None or now - lock.first_failed_at >= window_delta:
            lock.failed_count = 1
            lock.first_failed_at = now
        else:
            lock.failed_count += 1
        lock.last_failed_at = now
        lock.last_username = username[:64]

    should_block = lock.failed_count >= max(int(setting.local_ip_lock_max_attempts or 0), 1)
    if should_block:
        lock.blocked_until = now + window_delta

    write_operation_log(
        db,
        actor_id=None,
        action="LOGIN_FAILED",
        entity_type="SECURITY",
        entity_id=ip_address,
        detail=(
            f"ip={ip_address},username={username.strip()},failed_count={lock.failed_count},"
            f"blocked_until={lock.blocked_until.isoformat() if lock.blocked_until else ''}"
        ),
    )
    db.commit()
    return should_block


def clear_local_login_failures(db: Session, *, ip_address: str) -> None:
    lock = _get_ip_lock(db, ip_address)
    if lock is None:
        return
    db.delete(lock)
    db.commit()
