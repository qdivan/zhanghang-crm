from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, aliased

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models import DataAccessGrant, LdapSetting, OperationLog, User
from app.schemas.admin import (
    DataAccessGrantCreate,
    DataAccessGrantOut,
    DataAccessGrantUpdate,
    LdapSettingsOut,
    LdapSettingsUpdate,
    LdapSyncResponse,
    OperationLogOut,
)
from app.services.data_access import has_overlapping_active_grant
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
            detail="老板不能把 LDAP 默认角色设置为管理员",
        )


def _is_grant_effective(grant: DataAccessGrant) -> bool:
    if not grant.is_active:
        return False
    now = datetime.utcnow()
    if grant.starts_at is not None and grant.starts_at > now:
        return False
    if grant.ends_at is not None and grant.ends_at < now:
        return False
    return True


def _serialize_grant(grant: DataAccessGrant, grantee_username: str, grantor_username: Optional[str]) -> DataAccessGrantOut:
    return DataAccessGrantOut(
        id=grant.id,
        grantee_user_id=grant.grantee_user_id,
        grantee_username=grantee_username,
        module=grant.module,
        is_active=grant.is_active,
        is_effective=_is_grant_effective(grant),
        starts_at=grant.starts_at,
        ends_at=grant.ends_at,
        reason=grant.reason,
        granted_by_user_id=grant.granted_by_user_id,
        granted_by_username=grantor_username or "-",
        created_at=grant.created_at,
        updated_at=grant.updated_at,
    )


def _ensure_time_range_valid(starts_at: Optional[datetime], ends_at: Optional[datetime]) -> None:
    if starts_at is not None and ends_at is not None and ends_at <= starts_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="失效时间必须晚于生效时间",
        )


def _get_grant_or_404(db: Session, grant_id: int) -> DataAccessGrant:
    grant = db.execute(select(DataAccessGrant).where(DataAccessGrant.id == grant_id)).scalar_one_or_none()
    if grant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="数据授权不存在")
    return grant


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


@router.get("/data-access-grants", response_model=list[DataAccessGrantOut])
def list_data_access_grants(
    module: Optional[str] = Query(default=None),
    grantee_user_id: Optional[int] = Query(default=None),
    keyword: Optional[str] = Query(default=None),
    include_inactive: bool = Query(default=True),
    db: Session = Depends(get_db),
):
    grantee = aliased(User)
    grantor = aliased(User)
    stmt = (
        select(DataAccessGrant, grantee.username, grantor.username)
        .join(grantee, DataAccessGrant.grantee_user_id == grantee.id)
        .outerjoin(grantor, DataAccessGrant.granted_by_user_id == grantor.id)
        .order_by(DataAccessGrant.created_at.desc(), DataAccessGrant.id.desc())
    )
    if module:
        stmt = stmt.where(DataAccessGrant.module == module)
    if grantee_user_id:
        stmt = stmt.where(DataAccessGrant.grantee_user_id == grantee_user_id)
    if not include_inactive:
        stmt = stmt.where(DataAccessGrant.is_active.is_(True))
    if keyword:
        key = f"%{keyword.strip()}%"
        stmt = stmt.where(
            or_(
                grantee.username.ilike(key),
                grantor.username.ilike(key),
                DataAccessGrant.reason.ilike(key),
            )
        )

    rows = db.execute(stmt).all()
    return [_serialize_grant(grant, grantee_username, grantor_username) for grant, grantee_username, grantor_username in rows]


@router.post("/data-access-grants", response_model=DataAccessGrantOut, status_code=status.HTTP_201_CREATED)
def create_data_access_grant(
    payload: DataAccessGrantCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    grantee = db.execute(select(User).where(User.id == payload.grantee_user_id)).scalar_one_or_none()
    if grantee is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="被授权用户不存在")
    if grantee.role != "ACCOUNTANT":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="仅支持给会计账号授权")

    starts_at = payload.starts_at or datetime.utcnow()
    ends_at = payload.ends_at
    _ensure_time_range_valid(starts_at, ends_at)

    if payload.is_active and has_overlapping_active_grant(
        db,
        grantee_user_id=payload.grantee_user_id,
        module=payload.module,
        starts_at=starts_at,
        ends_at=ends_at,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该账号在该模块已有生效中的授权，请先停用旧授权",
        )

    grant = DataAccessGrant(
        grantee_user_id=payload.grantee_user_id,
        module=payload.module,
        is_active=payload.is_active,
        starts_at=starts_at,
        ends_at=ends_at,
        reason=payload.reason.strip(),
        granted_by_user_id=current_user.id,
    )
    db.add(grant)
    db.flush()
    write_operation_log(
        db,
        actor_id=current_user.id,
        action="DATA_ACCESS_GRANT_CREATED",
        entity_type="DATA_ACCESS_GRANT",
        entity_id=grant.id,
        detail=f"grantee={grantee.username},module={grant.module},active={grant.is_active}",
    )
    db.commit()
    db.refresh(grant)
    return _serialize_grant(grant, grantee.username, current_user.username)


@router.patch("/data-access-grants/{grant_id}", response_model=DataAccessGrantOut)
def update_data_access_grant(
    grant_id: int,
    payload: DataAccessGrantUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    grant = _get_grant_or_404(db, grant_id)
    grantee = db.execute(select(User).where(User.id == grant.grantee_user_id)).scalar_one_or_none()
    if grantee is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="被授权用户不存在")

    new_starts_at = payload.starts_at if payload.starts_at is not None else grant.starts_at
    new_ends_at = payload.ends_at if payload.ends_at is not None else grant.ends_at
    _ensure_time_range_valid(new_starts_at, new_ends_at)

    new_is_active = payload.is_active if payload.is_active is not None else grant.is_active
    if new_is_active and has_overlapping_active_grant(
        db,
        grantee_user_id=grant.grantee_user_id,
        module=grant.module,
        starts_at=new_starts_at,
        ends_at=new_ends_at,
        exclude_grant_id=grant.id,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该账号在该模块已有生效中的授权，请先停用旧授权",
        )

    old_is_active = grant.is_active
    changed_fields: list[str] = []
    if payload.starts_at is not None:
        grant.starts_at = payload.starts_at
        changed_fields.append("starts_at")
    if payload.ends_at is not None:
        grant.ends_at = payload.ends_at
        changed_fields.append("ends_at")
    if payload.reason is not None:
        grant.reason = payload.reason.strip()
        changed_fields.append("reason")
    if payload.is_active is not None:
        grant.is_active = payload.is_active
        changed_fields.append("is_active")

    action = "DATA_ACCESS_GRANT_UPDATED"
    if payload.is_active is False:
        action = "DATA_ACCESS_GRANT_REVOKED"
    if payload.is_active is True and not old_is_active:
        action = "DATA_ACCESS_GRANT_REACTIVATED"

    write_operation_log(
        db,
        actor_id=current_user.id,
        action=action,
        entity_type="DATA_ACCESS_GRANT",
        entity_id=grant.id,
        detail=f"changes={','.join(changed_fields) if changed_fields else 'none'}",
    )
    db.commit()
    db.refresh(grant)
    grantor = db.execute(select(User).where(User.id == grant.granted_by_user_id)).scalar_one_or_none()
    return _serialize_grant(grant, grantee.username, grantor.username if grantor else None)


@router.delete("/data-access-grants/{grant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_data_access_grant(
    grant_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    grant = _get_grant_or_404(db, grant_id)
    db.delete(grant)
    write_operation_log(
        db,
        actor_id=current_user.id,
        action="DATA_ACCESS_GRANT_DELETED",
        entity_type="DATA_ACCESS_GRANT",
        entity_id=grant_id,
        detail="deleted",
    )
    db.commit()
