from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models import LdapSetting, OperationLog, User
from app.schemas.admin import LdapSettingsOut, LdapSettingsUpdate, LdapSyncResponse, OperationLogOut
from app.services.audit import write_operation_log
from app.services.ldap_sync import get_or_create_ldap_setting, sync_ldap_users

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_roles("OWNER", "ADMIN"))])


def _to_ldap_settings_out(setting: LdapSetting) -> LdapSettingsOut:
    return LdapSettingsOut(
        id=setting.id,
        enabled=setting.enabled,
        server_url=setting.server_url,
        bind_dn=setting.bind_dn,
        has_bind_password=bool(setting.bind_password),
        base_dn=setting.base_dn,
        user_base_dn=setting.user_base_dn,
        user_filter=setting.user_filter,
        username_attr=setting.username_attr,
        display_name_attr=setting.display_name_attr,
        default_role=setting.default_role,
        created_at=setting.created_at,
        updated_at=setting.updated_at,
    )


def _ensure_owner_scope(current_user: User, target_role: str) -> None:
    if current_user.role == "OWNER" and target_role == "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Owner cannot set LDAP default role to ADMIN",
        )


@router.get("/ldap/settings", response_model=LdapSettingsOut)
def get_ldap_settings(
    db: Session = Depends(get_db),
):
    setting = get_or_create_ldap_setting(db)
    return _to_ldap_settings_out(setting)


@router.put("/ldap/settings", response_model=LdapSettingsOut)
def update_ldap_settings(
    payload: LdapSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    setting = get_or_create_ldap_setting(db)
    changed_fields: list[str] = []

    if payload.default_role is not None:
        _ensure_owner_scope(current_user, payload.default_role)

    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        if key == "bind_password":
            if value is not None:
                setting.bind_password = value
                changed_fields.append(key)
            continue
        setattr(setting, key, value)
        changed_fields.append(key)

    write_operation_log(
        db,
        actor_id=current_user.id,
        action="LDAP_SETTINGS_UPDATED",
        entity_type="LDAP",
        entity_id=setting.id,
        detail=f"fields={','.join(changed_fields) if changed_fields else 'none'}",
    )
    db.commit()
    db.refresh(setting)
    return _to_ldap_settings_out(setting)


@router.post("/ldap/sync", response_model=LdapSyncResponse, status_code=status.HTTP_200_OK)
def trigger_ldap_sync(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    setting = get_or_create_ldap_setting(db)
    sync_result = sync_ldap_users(db, setting)

    write_operation_log(
        db,
        actor_id=current_user.id,
        action="LDAP_SYNC",
        entity_type="LDAP",
        entity_id=setting.id,
        detail=(
            f"found={sync_result['total_found']},"
            f"created={sync_result['created_count']},"
            f"updated={sync_result['updated_count']},"
            f"skipped={sync_result['skipped_count']}"
        ),
    )
    db.commit()

    return LdapSyncResponse(
        **sync_result,
        message="LDAP 同步完成",
    )


@router.get("/operation-logs", response_model=list[OperationLogOut])
def list_operation_logs(
    action: Optional[str] = Query(default=None),
    entity_type: Optional[str] = Query(default=None),
    keyword: Optional[str] = Query(default=None),
    limit: int = Query(default=200, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = (
        select(OperationLog, User.username, User.role)
        .outerjoin(User, OperationLog.actor_id == User.id)
        .order_by(OperationLog.created_at.desc(), OperationLog.id.desc())
        .limit(limit)
    )
    if action:
        stmt = stmt.where(OperationLog.action == action)
    if entity_type:
        stmt = stmt.where(OperationLog.entity_type == entity_type)
    if keyword:
        key = f"%{keyword.strip()}%"
        stmt = stmt.where(
            or_(
                OperationLog.detail.ilike(key),
                OperationLog.entity_id.ilike(key),
                User.username.ilike(key),
            )
        )
    if current_user.role == "OWNER":
        stmt = stmt.where(or_(User.role != "ADMIN", User.role.is_(None)))

    rows = db.execute(stmt).all()
    result: list[OperationLogOut] = []
    for log, username, _role in rows:
        result.append(
            OperationLogOut(
                id=log.id,
                actor_id=log.actor_id,
                actor_username=username or "-",
                action=log.action,
                entity_type=log.entity_type,
                entity_id=log.entity_id,
                detail=log.detail,
                created_at=log.created_at,
            )
        )
    return result
