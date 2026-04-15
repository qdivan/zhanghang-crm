import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, aliased

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models import (
    AddressResource,
    AddressResourceCompany,
    BillingRecord,
    CommonLibraryItem,
    Customer,
    DataAccessGrant,
    LdapSetting,
    Lead,
    OperationLog,
    SsoBindingConflict,
    UserIdentity,
    SecuritySetting,
    TodoItem,
    User,
)
from app.schemas.admin import (
    DataAccessGrantCreate,
    DataAccessGrantOut,
    DataAccessGrantUpdate,
    DeletedRecordOut,
    DeletedRecordRestoreOut,
    LdapSettingsOut,
    LdapSettingsUpdate,
    LdapSyncResponse,
    OperationLogOut,
    SsoBindingManualCreate,
    SsoBindingOut,
    SsoConflictOut,
    SsoConflictResolve,
    SecuritySettingsOut,
    SecuritySettingsUpdate,
    SsoUnboundUserOut,
)
from app.services.data_access import has_overlapping_active_grant
from app.services.audit import write_operation_log
from app.services.login_security import get_or_create_security_setting
from app.services.ldap_sync import get_or_create_ldap_setting, sync_ldap_users
from app.services.sso import PROVIDER_KEYCLOAK, SsoError, create_manual_binding
from app.services.soft_delete import active_filter, deleted_filter, mark_deleted, restore_deleted

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


def _to_security_settings_out(setting: SecuritySetting) -> SecuritySettingsOut:
    return SecuritySettingsOut(
        id=setting.id,
        local_ip_lock_enabled=setting.local_ip_lock_enabled,
        local_ip_lock_window_minutes=setting.local_ip_lock_window_minutes,
        local_ip_lock_max_attempts=setting.local_ip_lock_max_attempts,
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
    grant = db.execute(select(DataAccessGrant).where(DataAccessGrant.id == grant_id, active_filter(DataAccessGrant))).scalar_one_or_none()
    if grant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="数据授权不存在")
    return grant


def _keyword_matches(keyword: Optional[str], *values: object) -> bool:
    raw = (keyword or "").strip().lower()
    if not raw:
        return True
    return any(raw in str(value or "").lower() for value in values)


def _grant_module_label(module: str) -> str:
    return "客户列表" if module == "CUSTOMER" else "收费明细"


def _to_deleted_record_out(
    *,
    entity_type: str,
    entity_id: int,
    display_name: str,
    detail: str,
    deleted_at: datetime,
    deleted_by_user_id: Optional[int],
    deleted_by_username: Optional[str],
) -> DeletedRecordOut:
    return DeletedRecordOut(
        entity_type=entity_type,
        entity_id=entity_id,
        display_name=display_name,
        detail=detail,
        deleted_at=deleted_at,
        deleted_by_user_id=deleted_by_user_id,
        deleted_by_username=deleted_by_username or "-",
    )


def _identity_to_out(identity: UserIdentity) -> SsoBindingOut:
    user = identity.user
    return SsoBindingOut(
        id=identity.id,
        user_id=identity.user_id,
        username=user.username if user is not None else "-",
        display_name=(user.display_name if user is not None else "") or identity.display_name or "",
        email=(user.email if user is not None else "") or identity.email or "",
        provider=identity.provider,
        issuer=identity.issuer,
        subject=identity.subject,
        preferred_username=identity.preferred_username,
        email_verified=identity.email_verified,
        external_managed=bool(user.external_managed) if user is not None else False,
        last_login_at=identity.last_login_at,
        created_at=identity.created_at,
        updated_at=identity.updated_at,
    )


def _conflict_to_out(db: Session, conflict: SsoBindingConflict) -> SsoConflictOut:
    candidate_ids = []
    try:
        parsed = json.loads(conflict.candidate_user_ids_json or "[]")
        if isinstance(parsed, list):
            candidate_ids = [int(item) for item in parsed if str(item).isdigit()]
    except Exception:
        candidate_ids = []
    candidate_names = []
    if candidate_ids:
        candidate_names = list(
            db.execute(select(User.username).where(User.id.in_(candidate_ids), active_filter(User))).scalars().all()
        )
    return SsoConflictOut(
        id=conflict.id,
        provider=conflict.provider,
        issuer=conflict.issuer,
        subject=conflict.subject,
        preferred_username=conflict.preferred_username,
        email=conflict.email,
        display_name=conflict.display_name,
        reason=conflict.reason,
        status=conflict.status,
        candidate_user_ids=candidate_ids,
        candidate_usernames=candidate_names,
        first_seen_at=conflict.first_seen_at,
        last_seen_at=conflict.last_seen_at,
        resolved_user_id=conflict.resolved_user_id,
        resolved_username=conflict.resolved_user.username if conflict.resolved_user is not None else "",
    )


def _resolve_matching_pending_sso_conflicts(
    db: Session,
    *,
    issuer: str,
    subject: str,
    user_id: int,
) -> list[SsoBindingConflict]:
    rows = db.execute(
        select(SsoBindingConflict).where(
            SsoBindingConflict.provider == PROVIDER_KEYCLOAK,
            SsoBindingConflict.issuer == issuer,
            SsoBindingConflict.subject == subject,
            SsoBindingConflict.status == "PENDING",
        )
    ).scalars().all()
    if not rows:
        return []
    now = datetime.utcnow()
    for row in rows:
        row.status = "RESOLVED"
        row.resolved_user_id = user_id
        row.resolved_at = now
    return rows


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


@router.get("/security-settings", response_model=SecuritySettingsOut)
def get_security_settings(
    db: Session = Depends(get_db),
):
    setting = get_or_create_security_setting(db)
    return _to_security_settings_out(setting)


@router.put("/security-settings", response_model=SecuritySettingsOut)
def update_security_settings(
    payload: SecuritySettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    setting = get_or_create_security_setting(db)
    changed_fields: list[str] = []
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(setting, key, value)
        changed_fields.append(key)

    write_operation_log(
        db,
        actor_id=current_user.id,
        action="SECURITY_SETTINGS_UPDATED",
        entity_type="SECURITY",
        entity_id=setting.id,
        detail=f"fields={','.join(changed_fields) if changed_fields else 'none'}",
    )
    db.commit()
    db.refresh(setting)
    return _to_security_settings_out(setting)


@router.get("/operation-logs", response_model=list[OperationLogOut])
def list_operation_logs(
    action: Optional[str] = Query(default=None),
    entity_type: Optional[str] = Query(default=None),
    audit_scope: Optional[str] = Query(default=None),
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
    normalized_audit_scope = (audit_scope or "").strip().upper()
    if normalized_audit_scope == "DELETE":
        stmt = stmt.where(OperationLog.action.ilike("%DELETED"))
    elif normalized_audit_scope == "RESTORE":
        stmt = stmt.where(OperationLog.action.ilike("%RESTORED"))
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


@router.get("/deleted-records", response_model=list[DeletedRecordOut])
def list_deleted_records(
    entity_type: Optional[str] = Query(default=None),
    keyword: Optional[str] = Query(default=None),
    limit: int = Query(default=200, ge=1, le=500),
    db: Session = Depends(get_db),
):
    normalized_type = (entity_type or "").strip().upper()
    deleted_by_user = aliased(User)
    per_type_limit = min(max(limit, 50), 500)
    results: list[DeletedRecordOut] = []

    if not normalized_type or normalized_type == "LEAD":
        rows = db.execute(
            select(Lead, deleted_by_user.username)
            .outerjoin(deleted_by_user, Lead.deleted_by_user_id == deleted_by_user.id)
            .where(deleted_filter(Lead))
            .order_by(Lead.deleted_at.desc(), Lead.id.desc())
            .limit(per_type_limit)
        ).all()
        for lead, deleted_by_username in rows:
            display_name = (lead.name or "").strip() or (lead.contact_name or "").strip() or f"线索#{lead.id}"
            detail = f"联系人：{(lead.contact_name or '').strip() or '-'}"
            if _keyword_matches(keyword, display_name, detail, lead.source, lead.main_business):
                results.append(
                    _to_deleted_record_out(
                        entity_type="LEAD",
                        entity_id=lead.id,
                        display_name=display_name,
                        detail=detail,
                        deleted_at=lead.deleted_at or lead.updated_at,
                        deleted_by_user_id=lead.deleted_by_user_id,
                        deleted_by_username=deleted_by_username,
                    )
                )

    if not normalized_type or normalized_type == "CUSTOMER":
        rows = db.execute(
            select(Customer, deleted_by_user.username)
            .outerjoin(deleted_by_user, Customer.deleted_by_user_id == deleted_by_user.id)
            .where(deleted_filter(Customer))
            .order_by(Customer.deleted_at.desc(), Customer.id.desc())
            .limit(per_type_limit)
        ).all()
        for customer, deleted_by_username in rows:
            display_name = (customer.name or "").strip() or (customer.contact_name or "").strip() or f"客户#{customer.id}"
            detail = f"联系人：{(customer.contact_name or '').strip() or '-'}"
            if _keyword_matches(keyword, display_name, detail, customer.phone):
                results.append(
                    _to_deleted_record_out(
                        entity_type="CUSTOMER",
                        entity_id=customer.id,
                        display_name=display_name,
                        detail=detail,
                        deleted_at=customer.deleted_at or customer.created_at,
                        deleted_by_user_id=customer.deleted_by_user_id,
                        deleted_by_username=deleted_by_username,
                    )
                )

    if not normalized_type or normalized_type == "BILLING":
        rows = db.execute(
            select(BillingRecord, deleted_by_user.username)
            .outerjoin(deleted_by_user, BillingRecord.deleted_by_user_id == deleted_by_user.id)
            .where(deleted_filter(BillingRecord))
            .order_by(BillingRecord.deleted_at.desc(), BillingRecord.id.desc())
            .limit(per_type_limit)
        ).all()
        for record, deleted_by_username in rows:
            summary_text = (record.summary or "").strip() or (record.charge_category or "").strip() or f"收费单#{record.serial_no or record.id}"
            display_name = f"{(record.customer_name or '').strip() or '未命名客户'} · {summary_text}"
            detail = f"序号：{record.serial_no}，总费用：{float(record.total_fee or 0):.2f}"
            if _keyword_matches(keyword, display_name, detail, record.note, record.charge_category):
                results.append(
                    _to_deleted_record_out(
                        entity_type="BILLING",
                        entity_id=record.id,
                        display_name=display_name,
                        detail=detail,
                        deleted_at=record.deleted_at or record.updated_at,
                        deleted_by_user_id=record.deleted_by_user_id,
                        deleted_by_username=deleted_by_username,
                    )
                )

    if not normalized_type or normalized_type == "TODO":
        rows = db.execute(
            select(TodoItem, deleted_by_user.username)
            .outerjoin(deleted_by_user, TodoItem.deleted_by_user_id == deleted_by_user.id)
            .where(deleted_filter(TodoItem))
            .order_by(TodoItem.deleted_at.desc(), TodoItem.id.desc())
            .limit(per_type_limit)
        ).all()
        for todo, deleted_by_username in rows:
            display_name = (todo.title or "").strip() or f"待办#{todo.id}"
            detail = f"优先级：{todo.priority or '-'}"
            if _keyword_matches(keyword, display_name, detail, todo.description):
                results.append(
                    _to_deleted_record_out(
                        entity_type="TODO",
                        entity_id=todo.id,
                        display_name=display_name,
                        detail=detail,
                        deleted_at=todo.deleted_at or todo.updated_at,
                        deleted_by_user_id=todo.deleted_by_user_id,
                        deleted_by_username=deleted_by_username,
                    )
                )

    if not normalized_type or normalized_type == "ADDRESS_RESOURCE":
        rows = db.execute(
            select(AddressResource, deleted_by_user.username)
            .outerjoin(deleted_by_user, AddressResource.deleted_by_user_id == deleted_by_user.id)
            .where(deleted_filter(AddressResource))
            .order_by(AddressResource.deleted_at.desc(), AddressResource.id.desc())
            .limit(per_type_limit)
        ).all()
        for resource, deleted_by_username in rows:
            display_name = (resource.category or "").strip() or (resource.contact_info or "").strip() or f"地址资源#{resource.id}"
            detail = f"联系人：{(resource.contact_info or '').strip() or '-'}"
            if _keyword_matches(keyword, display_name, detail, resource.description, resource.notes):
                results.append(
                    _to_deleted_record_out(
                        entity_type="ADDRESS_RESOURCE",
                        entity_id=resource.id,
                        display_name=display_name,
                        detail=detail,
                        deleted_at=resource.deleted_at or resource.updated_at,
                        deleted_by_user_id=resource.deleted_by_user_id,
                        deleted_by_username=deleted_by_username,
                    )
                )

    if not normalized_type or normalized_type == "ADDRESS_RESOURCE_COMPANY":
        rows = db.execute(
            select(AddressResourceCompany, deleted_by_user.username)
            .outerjoin(deleted_by_user, AddressResourceCompany.deleted_by_user_id == deleted_by_user.id)
            .where(deleted_filter(AddressResourceCompany))
            .order_by(AddressResourceCompany.deleted_at.desc(), AddressResourceCompany.id.desc())
            .limit(per_type_limit)
        ).all()
        for item, deleted_by_username in rows:
            display_name = (item.company_name or "").strip() or f"已服务公司#{item.id}"
            detail = f"挂靠地址ID：{item.address_resource_id}"
            if _keyword_matches(keyword, display_name, detail, item.notes):
                results.append(
                    _to_deleted_record_out(
                        entity_type="ADDRESS_RESOURCE_COMPANY",
                        entity_id=item.id,
                        display_name=display_name,
                        detail=detail,
                        deleted_at=item.deleted_at or item.updated_at,
                        deleted_by_user_id=item.deleted_by_user_id,
                        deleted_by_username=deleted_by_username,
                    )
                )

    if not normalized_type or normalized_type == "COMMON_LIBRARY":
        rows = db.execute(
            select(CommonLibraryItem, deleted_by_user.username)
            .outerjoin(deleted_by_user, CommonLibraryItem.deleted_by_user_id == deleted_by_user.id)
            .where(deleted_filter(CommonLibraryItem))
            .order_by(CommonLibraryItem.deleted_at.desc(), CommonLibraryItem.id.desc())
            .limit(per_type_limit)
        ).all()
        for item, deleted_by_username in rows:
            display_name = (item.title or "").strip() or (item.category or "").strip() or f"常用资料#{item.id}"
            detail = f"分类：{(item.category or '').strip() or '-'}"
            if _keyword_matches(keyword, display_name, detail, item.content, item.phone, item.address):
                results.append(
                    _to_deleted_record_out(
                        entity_type="COMMON_LIBRARY",
                        entity_id=item.id,
                        display_name=display_name,
                        detail=detail,
                        deleted_at=item.deleted_at or item.updated_at,
                        deleted_by_user_id=item.deleted_by_user_id,
                        deleted_by_username=deleted_by_username,
                    )
                )

    if not normalized_type or normalized_type == "USER":
        rows = db.execute(
            select(User, deleted_by_user.username)
            .outerjoin(deleted_by_user, User.deleted_by_user_id == deleted_by_user.id)
            .where(deleted_filter(User))
            .order_by(User.deleted_at.desc(), User.id.desc())
            .limit(per_type_limit)
        ).all()
        for user, deleted_by_username in rows:
            display_name = (user.username or "").strip() or f"用户#{user.id}"
            detail = f"角色：{user.role} / 来源：{'LDAP' if user.auth_source == 'LDAP' else '本地'}"
            if _keyword_matches(keyword, display_name, detail, user.role, user.auth_source):
                results.append(
                    _to_deleted_record_out(
                        entity_type="USER",
                        entity_id=user.id,
                        display_name=display_name,
                        detail=detail,
                        deleted_at=user.deleted_at or user.created_at,
                        deleted_by_user_id=user.deleted_by_user_id,
                        deleted_by_username=deleted_by_username,
                    )
                )

    if not normalized_type or normalized_type == "DATA_ACCESS_GRANT":
        grantee = aliased(User)
        rows = db.execute(
            select(DataAccessGrant, grantee.username, deleted_by_user.username)
            .join(grantee, DataAccessGrant.grantee_user_id == grantee.id)
            .outerjoin(deleted_by_user, DataAccessGrant.deleted_by_user_id == deleted_by_user.id)
            .where(deleted_filter(DataAccessGrant))
            .order_by(DataAccessGrant.deleted_at.desc(), DataAccessGrant.id.desc())
            .limit(per_type_limit)
        ).all()
        for grant, grantee_username, deleted_by_username in rows:
            display_name = f"{(grantee_username or '-').strip() or '-'} · {_grant_module_label(grant.module)}"
            detail = f"授权原因：{(grant.reason or '').strip() or '-'}"
            if _keyword_matches(keyword, display_name, detail, grant.reason, grant.module):
                results.append(
                    _to_deleted_record_out(
                        entity_type="DATA_ACCESS_GRANT",
                        entity_id=grant.id,
                        display_name=display_name,
                        detail=detail,
                        deleted_at=grant.deleted_at or grant.updated_at,
                        deleted_by_user_id=grant.deleted_by_user_id,
                        deleted_by_username=deleted_by_username,
                    )
                )

    results.sort(key=lambda item: (item.deleted_at, item.entity_type, item.entity_id), reverse=True)
    return results[:limit]


@router.post("/deleted-records/{entity_type}/{entity_id}/restore", response_model=DeletedRecordRestoreOut)
def restore_deleted_record(
    entity_type: str,
    entity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    normalized_type = (entity_type or "").strip().upper()
    display_name = f"{normalized_type}#{entity_id}"

    if normalized_type == "LEAD":
        lead = db.execute(select(Lead).where(Lead.id == entity_id, deleted_filter(Lead))).scalar_one_or_none()
        if lead is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="已删除线索不存在")
        restore_deleted(lead)
        display_name = (lead.name or "").strip() or (lead.contact_name or "").strip() or f"线索#{lead.id}"
        action = "LEAD_RESTORED"
    elif normalized_type == "CUSTOMER":
        customer = db.execute(select(Customer).where(Customer.id == entity_id, deleted_filter(Customer))).scalar_one_or_none()
        if customer is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="已删除客户不存在")
        restore_deleted(customer)
        source_lead = db.execute(select(Lead).where(Lead.id == customer.source_lead_id)).scalar_one_or_none()
        if source_lead is not None:
            source_lead.status = "CONVERTED"
            source_lead.updated_at = datetime.utcnow()
        display_name = (customer.name or "").strip() or (customer.contact_name or "").strip() or f"客户#{customer.id}"
        action = "CUSTOMER_RESTORED"
    elif normalized_type == "BILLING":
        record = db.execute(select(BillingRecord).where(BillingRecord.id == entity_id, deleted_filter(BillingRecord))).scalar_one_or_none()
        if record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="已删除收费单不存在")
        restore_deleted(record)
        summary_text = (record.summary or "").strip() or (record.charge_category or "").strip() or f"收费单#{record.serial_no or record.id}"
        display_name = f"{(record.customer_name or '').strip() or '未命名客户'} · {summary_text}"
        action = "BILLING_RECORD_RESTORED"
    elif normalized_type == "TODO":
        todo = db.execute(select(TodoItem).where(TodoItem.id == entity_id, deleted_filter(TodoItem))).scalar_one_or_none()
        if todo is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="已删除待办不存在")
        restore_deleted(todo)
        display_name = (todo.title or "").strip() or f"待办#{todo.id}"
        action = "TODO_RESTORED"
    elif normalized_type == "ADDRESS_RESOURCE":
        resource = db.execute(
            select(AddressResource).where(AddressResource.id == entity_id, deleted_filter(AddressResource))
        ).scalar_one_or_none()
        if resource is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="已删除挂靠地址不存在")
        restore_deleted(resource)
        display_name = (resource.category or "").strip() or (resource.contact_info or "").strip() or f"地址资源#{resource.id}"
        action = "ADDRESS_RESOURCE_RESTORED"
    elif normalized_type == "ADDRESS_RESOURCE_COMPANY":
        item = db.execute(
            select(AddressResourceCompany).where(AddressResourceCompany.id == entity_id, deleted_filter(AddressResourceCompany))
        ).scalar_one_or_none()
        if item is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="已删除已服务公司不存在")
        parent = db.execute(select(AddressResource).where(AddressResource.id == item.address_resource_id)).scalar_one_or_none()
        if parent is None or parent.is_deleted:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请先恢复所属挂靠地址")
        restore_deleted(item)
        display_name = (item.company_name or "").strip() or f"已服务公司#{item.id}"
        action = "ADDRESS_RESOURCE_COMPANY_RESTORED"
    elif normalized_type == "COMMON_LIBRARY":
        item = db.execute(
            select(CommonLibraryItem).where(CommonLibraryItem.id == entity_id, deleted_filter(CommonLibraryItem))
        ).scalar_one_or_none()
        if item is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="已删除常用资料不存在")
        restore_deleted(item)
        display_name = (item.title or "").strip() or (item.category or "").strip() or f"常用资料#{item.id}"
        action = "COMMON_LIBRARY_ITEM_RESTORED"
    elif normalized_type == "USER":
        user = db.execute(select(User).where(User.id == entity_id, deleted_filter(User))).scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="已删除用户不存在")
        restore_deleted(user)
        display_name = (user.username or "").strip() or f"用户#{user.id}"
        action = "USER_RESTORED"
    elif normalized_type == "DATA_ACCESS_GRANT":
        grant = db.execute(
            select(DataAccessGrant).where(DataAccessGrant.id == entity_id, deleted_filter(DataAccessGrant))
        ).scalar_one_or_none()
        if grant is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="已删除数据授权不存在")
        grantee = db.execute(select(User).where(User.id == grant.grantee_user_id, active_filter(User))).scalar_one_or_none()
        if grantee is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请先恢复被授权账号")
        restore_deleted(grant)
        display_name = f"{(grantee.username or '-').strip() or '-'} · {_grant_module_label(grant.module)}"
        action = "DATA_ACCESS_GRANT_RESTORED"
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不支持的恢复类型")

    restored_at = datetime.utcnow()
    write_operation_log(
        db,
        actor_id=current_user.id,
        action=action,
        entity_type=normalized_type,
        entity_id=entity_id,
        detail=display_name,
    )
    db.commit()
    return DeletedRecordRestoreOut(
        entity_type=normalized_type,
        entity_id=entity_id,
        display_name=display_name,
        restored_at=restored_at,
    )


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
        .where(active_filter(DataAccessGrant))
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
    grantee = db.execute(select(User).where(User.id == payload.grantee_user_id, active_filter(User))).scalar_one_or_none()
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
    grantee = db.execute(select(User).where(User.id == grant.grantee_user_id, active_filter(User))).scalar_one_or_none()
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
    grantor = db.execute(select(User).where(User.id == grant.granted_by_user_id, active_filter(User))).scalar_one_or_none()
    return _serialize_grant(grant, grantee.username, grantor.username if grantor else None)


@router.delete("/data-access-grants/{grant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_data_access_grant(
    grant_id: int,
    confirm_name: str = Query(default=""),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    grant = _get_grant_or_404(db, grant_id)
    grantee = db.execute(select(User).where(User.id == grant.grantee_user_id)).scalar_one_or_none()
    expected_name = f"{(grantee.username if grantee is not None else '-').strip() or '-'} · {_grant_module_label(grant.module)}"
    if confirm_name.strip() != expected_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="确认名称不匹配")
    mark_deleted(grant, current_user.id)
    write_operation_log(
        db,
        actor_id=current_user.id,
        action="DATA_ACCESS_GRANT_DELETED",
        entity_type="DATA_ACCESS_GRANT",
        entity_id=grant_id,
        detail=expected_name,
    )
    db.commit()


@router.get("/sso/bindings", response_model=list[SsoBindingOut])
def list_sso_bindings(
    keyword: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    stmt = (
        select(UserIdentity)
        .join(User, UserIdentity.user_id == User.id)
        .where(UserIdentity.provider == PROVIDER_KEYCLOAK, active_filter(User))
        .order_by(UserIdentity.updated_at.desc(), UserIdentity.id.desc())
    )
    if keyword:
        key = f"%{keyword.strip()}%"
        stmt = stmt.where(
            or_(
                User.username.ilike(key),
                User.email.ilike(key),
                User.display_name.ilike(key),
                UserIdentity.email.ilike(key),
                UserIdentity.preferred_username.ilike(key),
                UserIdentity.subject.ilike(key),
            )
        )
    rows = db.execute(stmt).scalars().all()
    return [_identity_to_out(item) for item in rows]


@router.get("/sso/unbound-users", response_model=list[SsoUnboundUserOut])
def list_unbound_sso_users(
    keyword: Optional[str] = Query(default=None),
    include_inactive: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    binding_exists = (
        select(UserIdentity.id)
        .where(UserIdentity.user_id == User.id, UserIdentity.provider == PROVIDER_KEYCLOAK)
        .exists()
    )
    stmt = (
        select(User)
        .where(active_filter(User))
        .where(~binding_exists)
        .order_by(User.created_at.desc(), User.id.desc())
    )
    if not include_inactive:
        stmt = stmt.where(User.is_active.is_(True))
    if keyword:
        key = f"%{keyword.strip()}%"
        stmt = stmt.where(
            or_(
                User.username.ilike(key),
                User.email.ilike(key),
                User.display_name.ilike(key),
            )
        )
    rows = db.execute(stmt).scalars().all()
    return [
        SsoUnboundUserOut(
            id=user.id,
            username=user.username,
            display_name=user.display_name or "",
            email=user.email or "",
            auth_source=user.auth_source,
            external_managed=bool(user.external_managed),
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at,
        )
        for user in rows
    ]


@router.get("/sso/conflicts", response_model=list[SsoConflictOut])
def list_sso_conflicts(
    status_filter: str = Query(default="PENDING"),
    keyword: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    stmt = select(SsoBindingConflict).order_by(
        SsoBindingConflict.status.asc(),
        SsoBindingConflict.last_seen_at.desc(),
        SsoBindingConflict.id.desc(),
    )
    if status_filter and status_filter != "ALL":
        stmt = stmt.where(SsoBindingConflict.status == status_filter)
    if keyword:
        key = f"%{keyword.strip()}%"
        stmt = stmt.where(
            or_(
                SsoBindingConflict.email.ilike(key),
                SsoBindingConflict.display_name.ilike(key),
                SsoBindingConflict.preferred_username.ilike(key),
                SsoBindingConflict.subject.ilike(key),
                SsoBindingConflict.reason.ilike(key),
            )
        )
    rows = db.execute(stmt).scalars().all()
    return [_conflict_to_out(db, row) for row in rows]


@router.post("/sso/bindings/manual", response_model=SsoBindingOut, status_code=status.HTTP_201_CREATED)
def create_sso_binding_manual(
    payload: SsoBindingManualCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user = db.execute(select(User).where(User.id == payload.user_id, active_filter(User))).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="本地用户不存在")
    try:
        identity = create_manual_binding(
            db,
            user=user,
            issuer=payload.issuer.strip(),
            subject=payload.subject.strip(),
            preferred_username=payload.preferred_username.strip(),
            email=payload.email.strip(),
            email_verified=payload.email_verified,
            display_name=payload.display_name.strip(),
            raw_claims_json=payload.raw_claims_json.strip(),
        )
    except SsoError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    write_operation_log(
        db,
        actor_id=current_user.id,
        action="SSO_BINDING_CREATED",
        entity_type="USER_IDENTITY",
        entity_id=identity.id,
        detail=f"user={user.username},subject={identity.subject}",
    )
    resolved_conflicts = _resolve_matching_pending_sso_conflicts(
        db,
        issuer=identity.issuer,
        subject=identity.subject,
        user_id=user.id,
    )
    for conflict in resolved_conflicts:
        write_operation_log(
            db,
            actor_id=current_user.id,
            action="SSO_CONFLICT_RESOLVED",
            entity_type="SSO_CONFLICT",
            entity_id=conflict.id,
            detail=f"user={user.username},subject={identity.subject},method=manual-binding",
        )
    db.commit()
    db.refresh(identity)
    return _identity_to_out(identity)


@router.post("/sso/conflicts/{conflict_id}/resolve", response_model=SsoBindingOut)
def resolve_sso_conflict(
    conflict_id: int,
    payload: SsoConflictResolve,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conflict = db.execute(select(SsoBindingConflict).where(SsoBindingConflict.id == conflict_id)).scalar_one_or_none()
    if conflict is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SSO 绑定冲突不存在")
    user = db.execute(select(User).where(User.id == payload.user_id, active_filter(User))).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="本地用户不存在")
    try:
        identity = create_manual_binding(
            db,
            user=user,
            issuer=conflict.issuer,
            subject=conflict.subject,
            preferred_username=conflict.preferred_username,
            email=conflict.email,
            display_name=conflict.display_name,
            raw_claims_json=conflict.raw_claims_json,
        )
    except SsoError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    conflict.status = "RESOLVED"
    conflict.resolved_user_id = user.id
    conflict.resolved_at = datetime.utcnow()
    write_operation_log(
        db,
        actor_id=current_user.id,
        action="SSO_CONFLICT_RESOLVED",
        entity_type="SSO_CONFLICT",
        entity_id=conflict.id,
        detail=f"user={user.username},subject={conflict.subject}",
    )
    db.commit()
    db.refresh(identity)
    return _identity_to_out(identity)


@router.delete("/sso/bindings/{binding_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sso_binding(
    binding_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    identity = db.execute(select(UserIdentity).where(UserIdentity.id == binding_id)).scalar_one_or_none()
    if identity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SSO 绑定不存在")
    user = identity.user
    subject = identity.subject
    db.delete(identity)
    db.flush()
    if user is not None:
        remaining = db.execute(
            select(func.count(UserIdentity.id)).where(UserIdentity.user_id == user.id)
        ).scalar_one()
        if int(remaining or 0) == 0:
            user.external_managed = False
    write_operation_log(
        db,
        actor_id=current_user.id,
        action="SSO_BINDING_REMOVED",
        entity_type="USER_IDENTITY",
        entity_id=binding_id,
        detail=f"user={(user.username if user is not None else '-')},subject={subject}",
    )
    db.commit()
