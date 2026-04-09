from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.orm import Session, aliased, selectinload

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models import (
    AddressResourceCompany,
    BillingActivity,
    BillingExecutionLog,
    BillingPayment,
    BillingRecord,
    Customer,
    CustomerTimelineEvent,
    Lead,
    LeadFollowup,
    OperationLog,
    User,
)
from app.schemas.customer import (
    CustomerDetailOut,
    CustomerDeleteBlockerOut,
    CustomerImportResultOut,
    CustomerImportRowResultOut,
    CustomerListOut,
    CustomerMatterSummaryOut,
    CustomerSuggestOut,
    CustomerTimelineEntryOut,
    CustomerTimelineEventCreate,
    CustomerTimelineEventOut,
    CustomerTimelineEventUpdate,
    CustomerUpdate,
)
from app.services.audit import write_operation_log
from app.services.customer_spreadsheet import (
    build_customer_export_bytes,
    build_customer_template_bytes,
    parse_customer_import_file,
)
from app.services.customer_scope import customer_owned_by_any_condition, customer_owned_by_user_condition
from app.services.data_access import has_module_read_grant
from app.services.org_scope import get_manager_subordinate_ids
from app.services.soft_delete import active_filter, mark_deleted

router = APIRouter(prefix="/customers", tags=["customers"])

CUSTOMER_SORT_FIELDS = {
    "id": Customer.id,
    "name": func.lower(Customer.name),
    "customer_code": func.lower(Customer.customer_code),
    "contact_name": func.lower(Customer.contact_name),
    "created_at": Customer.created_at,
}


def _get_customer_or_404(db: Session, customer_id: int) -> Customer:
    customer = db.execute(select(Customer).where(Customer.id == customer_id, active_filter(Customer))).scalar_one_or_none()
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return customer


def _apply_customer_scope_stmt(stmt, db: Session, current_user: User):
    has_customer_read_grant = False
    if current_user.role == "ACCOUNTANT":
        has_customer_read_grant = has_module_read_grant(db, current_user.id, "CUSTOMER")
    if current_user.role == "MANAGER":
        managed_ids = [current_user.id, *get_manager_subordinate_ids(db, current_user.id)]
        stmt = stmt.where(customer_owned_by_any_condition(managed_ids))
    elif current_user.role == "ACCOUNTANT" and not has_customer_read_grant:
        stmt = stmt.where(customer_owned_by_user_condition(current_user.id))
    return stmt


def _normalize_sort_order(value: Optional[str], default: str = "desc") -> str:
    token = (value or default).strip().lower()
    return "asc" if token == "asc" else "desc"


def _normalize_customer_sort_field(value: Optional[str]) -> str:
    token = (value or "id").strip().lower()
    return token if token in CUSTOMER_SORT_FIELDS or token == "accountant" else "id"


def _apply_customer_sort(stmt, sort_by: Optional[str], sort_order: Optional[str], *, accountant_username_column=None):
    field = _normalize_customer_sort_field(sort_by)
    direction = _normalize_sort_order(sort_order, "desc")
    order_column = CUSTOMER_SORT_FIELDS[field]
    if field == "accountant" and accountant_username_column is not None:
        order_column = func.lower(accountant_username_column)
    order_fn = asc if direction == "asc" else desc
    return stmt.order_by(order_fn(order_column), Customer.id.desc())


def _customer_service_start_display(lead: Lead) -> str:
    return (lead.service_start_text or "").strip() or (lead.contact_start_date.isoformat() if lead.contact_start_date else "")


def _format_customer_code(seq: Optional[int], suffix: str) -> str:
    if not seq:
        return ""
    token = str(int(seq)).zfill(4)
    postfix = (suffix or "").strip().upper()
    return f"{token}{postfix}" if postfix else token


def _default_customer_code_suffix(source: str, intro: str) -> str:
    normalized_source = (source or "").strip()
    normalized_intro = (intro or "").strip()
    if normalized_source == "Sally直播":
        return "S"
    if normalized_source == "麦总":
        return "M"
    if normalized_intro == "麦总":
        return "M"
    return "A"


def _next_customer_code_seq(db: Session) -> int:
    current_max = db.execute(select(func.max(Customer.customer_code_seq))).scalar() or 0
    return int(current_max) + 1


def _normalize_text(value: object) -> str:
    return str(value or "").strip()


def _parse_date_text(value: str) -> Optional[date]:
    raw = _normalize_text(value)
    if not raw:
        return None
    normalized = raw.replace(".", "-").replace("/", "-")
    if len(normalized) == 7:
        normalized = f"{normalized}-01"
    if len(normalized) >= 10:
        normalized = normalized[:10]
    try:
        return date.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(f"日期格式不正确：{raw}") from exc


def _parse_customer_code(value: str) -> tuple[int, str]:
    raw = _normalize_text(value).upper()
    if not raw:
        raise ValueError("客户编号不能为空")
    digit_part = ""
    suffix_part = ""
    for char in raw:
        if char.isdigit() and not suffix_part:
            digit_part += char
            continue
        suffix_part += char
    if not digit_part:
        raise ValueError(f"客户编号格式不正确：{raw}")
    return int(digit_part), suffix_part


def _resolve_import_accountant_id(
    db: Session,
    current_user: User,
    username: str,
    *,
    existing_customer: Optional[Customer] = None,
) -> int:
    normalized = _normalize_text(username)
    if not normalized:
        if existing_customer is not None and existing_customer.assigned_accountant_id is not None:
            return existing_customer.assigned_accountant_id
        raise ValueError("新增客户必须填写会计账号")
    accountant = db.execute(
        select(User).where(
            User.username == normalized,
            active_filter(User),
        )
    ).scalar_one_or_none()
    if accountant is None or not accountant.is_active:
        raise ValueError(f"会计账号不存在或已停用：{normalized}")
    if accountant.role != "ACCOUNTANT":
        raise ValueError(f"该账号不是会计：{normalized}")
    if current_user.role == "MANAGER":
        managed_ids = set(get_manager_subordinate_ids(db, current_user.id))
        if accountant.id not in managed_ids:
            raise ValueError(f"部门经理不能把客户导入给非直属会计：{normalized}")
    return accountant.id


def _find_customer_for_import(
    db: Session,
    *,
    customer_id_text: str,
    customer_code_text: str,
) -> Optional[Customer]:
    normalized_id = _normalize_text(customer_id_text)
    normalized_code = _normalize_text(customer_code_text).upper()

    customer_by_id: Optional[Customer] = None
    customer_by_code: Optional[Customer] = None

    if normalized_id:
        if not normalized_id.isdigit():
            raise ValueError(f"客户ID不是有效数字：{normalized_id}")
        customer_by_id = db.execute(
            select(Customer).where(Customer.id == int(normalized_id), active_filter(Customer))
        ).scalar_one_or_none()
        if customer_by_id is None:
            raise ValueError(f"客户ID不存在或已删除：{normalized_id}")

    if normalized_code:
        customer_by_code = db.execute(
            select(Customer).where(Customer.customer_code == normalized_code, active_filter(Customer))
        ).scalar_one_or_none()
        if customer_by_id is not None and customer_by_code is not None and customer_by_id.id != customer_by_code.id:
            raise ValueError("客户ID与客户编号对应的不是同一位客户")

    return customer_by_id or customer_by_code


def _serialize_customer_export_row(customer: Customer, lead: Lead, accountant_username: str) -> dict[str, object]:
    return {
        "customer_id": customer.id,
        "customer_code": customer.customer_code or _format_customer_code(customer.customer_code_seq, customer.customer_code_suffix),
        "name": customer.name,
        "contact_name": customer.contact_name,
        "phone": customer.phone,
        "status": customer.status,
        "accountant_username": accountant_username,
        "grade": lead.grade or "",
        "region": lead.region or "",
        "country": lead.country or "",
        "service_start_text": lead.service_start_text or "",
        "company_nature": lead.company_nature or "",
        "service_mode": lead.service_mode or "",
        "contact_wechat": lead.contact_wechat or "",
        "other_contact": lead.other_contact or "",
        "main_business": lead.main_business or "",
        "source": lead.source or "",
        "intro": lead.intro or "",
        "fee_standard": lead.fee_standard or "",
        "first_billing_period": lead.first_billing_period or "",
        "reminder_value": lead.reminder_value or "",
        "next_reminder_at": lead.next_reminder_at,
        "notes": lead.notes or "",
    }


def _build_customer_delete_blockers(db: Session, customer: Customer) -> list[CustomerDeleteBlockerOut]:
    blockers: list[CustomerDeleteBlockerOut] = []

    billing_count = (
        db.execute(
            select(func.count(BillingRecord.id)).where(
                BillingRecord.customer_id == customer.id,
                active_filter(BillingRecord),
            )
        ).scalar()
        or 0
    )
    if billing_count > 0:
        blockers.append(
            CustomerDeleteBlockerOut(
                type="BILLING_RECORD",
                count=int(billing_count),
                label="收费项目",
                message="该客户下还有收费项目，请先删除或处理收费项目后再删除客户。",
                href=f"/billing?view=records&customerId={customer.id}&focusDependency=1",
                filters={"view": "records", "customerId": customer.id, "focusDependency": 1},
            )
        )

    payment_count = (
        db.execute(
            select(func.count(BillingPayment.id)).where(
                BillingPayment.customer_id == customer.id,
                active_filter(BillingPayment),
            )
        ).scalar()
        or 0
    )
    if payment_count > 0:
        blockers.append(
            CustomerDeleteBlockerOut(
                type="BILLING_PAYMENT",
                count=int(payment_count),
                label="收款单",
                message="该客户下还有收款单，请先删除或冲正收款单后再删除客户。",
                href=f"/billing?view=payments&customerId={customer.id}&focusDependency=1",
                filters={"view": "payments", "customerId": customer.id, "focusDependency": 1},
            )
        )

    matter_count = (
        db.execute(
            select(func.count(CustomerTimelineEvent.id)).where(CustomerTimelineEvent.customer_id == customer.id)
        ).scalar()
        or 0
    )
    if matter_count > 0:
        blockers.append(
            CustomerDeleteBlockerOut(
                type="CUSTOMER_MATTER",
                count=int(matter_count),
                label="重要事项",
                message="该客户还有重要事项或客户记录，请先处理后再删除客户。",
                href=f"/customer-matters?customerId={customer.id}",
                filters={"customerId": customer.id},
            )
        )

    address_count = (
        db.execute(
            select(func.count(AddressResourceCompany.id)).where(
                AddressResourceCompany.customer_id == customer.id,
                active_filter(AddressResourceCompany),
            )
        ).scalar()
        or 0
    )
    if address_count > 0:
        blockers.append(
            CustomerDeleteBlockerOut(
                type="ADDRESS_RESOURCE_COMPANY",
                count=int(address_count),
                label="挂靠地址服务公司",
                message="该客户仍关联挂靠地址服务公司，请先移除地址关联后再删除客户。",
                href=f"/address-resources?customerId={customer.id}",
                filters={"customerId": customer.id},
            )
        )

    return blockers


def _ensure_customer_access(
    customer: Customer,
    current_user: User,
    db: Session,
    *,
    for_write: bool = False,
) -> None:
    if current_user.role not in {"ACCOUNTANT", "MANAGER"}:
        return
    if current_user.role == "MANAGER":
        managed_ids = {current_user.id, *get_manager_subordinate_ids(db, current_user.id)}
        if (
            customer.responsible_user_id in managed_ids
            or customer.assigned_accountant_id in managed_ids
        ):
            return
    else:
        if current_user.id in {customer.responsible_user_id, customer.assigned_accountant_id}:
            return
        if not for_write and has_module_read_grant(db, current_user.id, "CUSTOMER"):
            return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to this customer")


def _timeline_event_label(event_type: str) -> str:
    mapping = {
        "COMMUNICATION": "客户沟通",
        "MEETING": "内部讨论",
        "DELIVERY": "办理事项",
        "DOCUMENT": "资料/证照",
        "FEE_NOTE": "费用备注",
        "OTHER": "其他记录",
    }
    return mapping.get(event_type, event_type or "客户记录")


def _timeline_event_status_label(status_value: str) -> str:
    mapping = {
        "NOTE": "仅记录",
        "OPEN": "待跟进",
        "DONE": "已办结",
    }
    return mapping.get((status_value or "").strip().upper(), "仅记录")


def _normalize_customer_event_status(status_value: str) -> str:
    normalized = (status_value or "NOTE").strip().upper()
    if normalized not in {"NOTE", "OPEN", "DONE"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="客户记录状态不合法")
    return normalized


def _build_customer_event_extra(item: CustomerTimelineEvent) -> str:
    return _join_note_parts(
        f"状态：{_timeline_event_status_label(item.status)}",
        f"提醒：{item.reminder_at}" if item.reminder_at else "",
        f"办结：{item.completed_at}" if item.completed_at else "",
        f"结果：{(item.result or '').strip()}" if (item.result or "").strip() else "",
    )


def _parse_customer_base_date(customer: Customer, lead: Lead) -> date:
    candidates = [
        (lead.service_start_text or "").strip(),
        (lead.contact_start_date.isoformat() if lead.contact_start_date else ""),
    ]
    for item in candidates:
        if not item:
            continue
        try:
            return date.fromisoformat(item)
        except ValueError:
            continue
    return customer.created_at.date()


def _safe_anniversary(year: int, month: int, day: int) -> date:
    try:
        return date(year, month, day)
    except ValueError:
        if month == 2 and day == 29:
            return date(year, 2, 28)
        raise


def _next_anniversary(base_date: date, today: Optional[date] = None) -> date:
    current = today or date.today()
    anniversary = _safe_anniversary(current.year, base_date.month, base_date.day)
    if anniversary < current:
        anniversary = _safe_anniversary(current.year + 1, base_date.month, base_date.day)
    return anniversary


def _build_hk_company_template_events(customer: Customer, lead: Lead, actor_id: int) -> list[CustomerTimelineEvent]:
    base_date = _parse_customer_base_date(customer, lead)
    anniversary = _next_anniversary(base_date)
    created_on = date.today()
    return [
        CustomerTimelineEvent(
            customer_id=customer.id,
            occurred_at=created_on,
            event_type="DOCUMENT",
            status="OPEN",
            reminder_at=anniversary - timedelta(days=45),
            template_key="HK_COMPANY",
            content="香港公司年审资料准备",
            note="提前确认董事、股东、注册地址、秘书服务是否有变化，并提醒客户准备资料。",
            actor_id=actor_id,
        ),
        CustomerTimelineEvent(
            customer_id=customer.id,
            occurred_at=created_on,
            event_type="DELIVERY",
            status="OPEN",
            reminder_at=anniversary - timedelta(days=30),
            template_key="HK_COMPANY",
            content="香港公司商业登记证续期检查",
            note="确认商业登记证续期时间、应缴费用和付款安排。",
            actor_id=actor_id,
        ),
        CustomerTimelineEvent(
            customer_id=customer.id,
            occurred_at=created_on,
            event_type="DELIVERY",
            status="OPEN",
            reminder_at=anniversary - timedelta(days=15),
            template_key="HK_COMPANY",
            content="香港公司年审办理与结果回填",
            note="办理完成后请补充结果、费用和异常情况，便于会计与老板后续查询。",
            actor_id=actor_id,
        ),
    ]


def _execution_label(progress_type: str) -> str:
    mapping = {
        "UPDATE": "执行更新",
        "MILESTONE": "关键节点",
        "BLOCKER": "阻塞问题",
        "DONE": "办理完成",
    }
    return mapping.get(progress_type, progress_type or "执行进度")


def _money_text(amount: Optional[float]) -> str:
    if amount is None:
        return ""
    text = f"{float(amount):.2f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def _join_note_parts(*parts: str) -> str:
    return "；".join([part for part in parts if part])


def _build_customer_timeline(db: Session, customer: Customer, lead: Lead) -> list[CustomerTimelineEntryOut]:
    owner = db.execute(select(User).where(User.id == lead.owner_id)).scalar_one_or_none()
    responsible_name = customer.responsible_username or customer.accountant_username or str(customer.responsible_user_id or customer.assigned_accountant_id or "")

    followups = db.execute(
        select(LeadFollowup)
        .options(selectinload(LeadFollowup.creator))
        .where(LeadFollowup.lead_id == lead.id)
        .order_by(LeadFollowup.followup_at.desc(), LeadFollowup.id.desc())
    ).scalars().all()

    customer_events = db.execute(
        select(CustomerTimelineEvent)
        .options(selectinload(CustomerTimelineEvent.actor))
        .where(CustomerTimelineEvent.customer_id == customer.id)
        .order_by(CustomerTimelineEvent.occurred_at.desc(), CustomerTimelineEvent.id.desc())
    ).scalars().all()

    records = db.execute(
        select(BillingRecord)
        .where(BillingRecord.customer_id == customer.id, active_filter(BillingRecord))
        .order_by(BillingRecord.id.desc())
    ).scalars().all()
    record_ids = [item.id for item in records]
    serial_keys = [str(item.serial_no) for item in records]

    activities: list[BillingActivity] = []
    execution_logs: list[BillingExecutionLog] = []
    if record_ids:
        activities = db.execute(
            select(BillingActivity)
            .options(selectinload(BillingActivity.actor))
            .where(BillingActivity.billing_record_id.in_(record_ids))
            .order_by(BillingActivity.occurred_at.desc(), BillingActivity.id.desc())
        ).scalars().all()
        execution_logs = db.execute(
            select(BillingExecutionLog)
            .options(selectinload(BillingExecutionLog.actor))
            .where(BillingExecutionLog.billing_record_id.in_(record_ids))
            .order_by(BillingExecutionLog.occurred_at.desc(), BillingExecutionLog.id.desc())
        ).scalars().all()

    convert_log_row = db.execute(
        select(OperationLog, User.username)
        .outerjoin(User, OperationLog.actor_id == User.id)
        .where(
            OperationLog.action == "LEAD_CONVERTED",
            OperationLog.entity_type == "LEAD",
            OperationLog.entity_id == str(lead.id),
        )
        .order_by(OperationLog.created_at.desc(), OperationLog.id.desc())
        .limit(1)
    ).first()

    record_log_actor_map: dict[str, str] = {}
    if serial_keys:
        record_log_rows = db.execute(
            select(OperationLog, User.username)
            .outerjoin(User, OperationLog.actor_id == User.id)
            .where(
                OperationLog.action.in_(["BILLING_RECORD_CREATED", "BILLING_RECORD_RENEWED"]),
                OperationLog.entity_id.in_(serial_keys),
            )
            .order_by(OperationLog.created_at.asc(), OperationLog.id.asc())
        ).all()
        for log, username in record_log_rows:
            record_log_actor_map[str(log.entity_id)] = username or ""

    timeline_rows: list[tuple[object, int, int, CustomerTimelineEntryOut]] = []

    timeline_rows.append(
        (
            lead.contact_start_date or lead.created_at.date(),
            70,
            int(lead.id),
            CustomerTimelineEntryOut(
                occurred_at=lead.contact_start_date or lead.created_at.date(),
                source_type="LEAD_CREATED",
                source_id=lead.id,
                title="开始开发",
                content=(lead.source or "").strip() or f"线索已录入，模板：{lead.template_type}",
                note=(lead.notes or "").strip(),
                actor_username=owner.username if owner else "",
                extra=f"联系人：{lead.contact_name}" if lead.contact_name else "",
            ),
        )
    )

    for item in followups:
        timeline_rows.append(
            (
                item.followup_at,
                60,
                int(item.id),
                CustomerTimelineEntryOut(
                    occurred_at=item.followup_at,
                    source_type="LEAD_FOLLOWUP",
                    source_id=item.id,
                    title="开发跟进",
                    content=(item.feedback or "").strip() or "开发阶段跟进",
                    note=(item.notes or "").strip(),
                    actor_username=(item.created_by_username or "").strip(),
                    extra=f"下次提醒：{item.next_reminder_at}" if item.next_reminder_at else "",
                ),
            )
        )

    if convert_log_row is not None:
        log, username = convert_log_row
        timeline_rows.append(
            (
                log.created_at.date(),
                55,
                int(lead.id),
                CustomerTimelineEntryOut(
                    occurred_at=log.created_at.date(),
                    source_type="CONVERTED",
                    source_id=lead.id,
                    title="客户成单",
                    content=f"已转入客户列表，并分配负责人员 {responsible_name or '-'}",
                    note="",
                    actor_username=username or "",
                    extra="",
                ),
            )
        )

    for record in records:
        summary = (record.summary or "").strip() or (record.note or "").strip() or f"收费单#{record.serial_no}"
        timeline_rows.append(
            (
                record.created_at.date(),
                50,
                int(record.id),
                CustomerTimelineEntryOut(
                    occurred_at=record.created_at.date(),
                    source_type="BILLING_RECORD",
                    source_id=record.id,
                    title="收费单创建",
                    content=summary,
                    note=_join_note_parts(
                        f"总费用 {_money_text(record.total_fee)}",
                        f"付款方式 {record.payment_method}" if record.payment_method else "",
                        f"到期 {record.due_month}" if record.due_month else "",
                    ),
                    actor_username=record_log_actor_map.get(str(record.serial_no), ""),
                    extra=f"序号 {record.serial_no}",
                ),
            )
        )

    for item in activities:
        amount_text = _money_text(item.amount)
        timeline_rows.append(
            (
                item.occurred_at,
                40,
                int(item.id),
                CustomerTimelineEntryOut(
                    occurred_at=item.occurred_at,
                    source_type="BILLING_ACTIVITY",
                    source_id=item.id,
                    title="收款记录" if item.activity_type == "PAYMENT" else "催收记录",
                    content=(item.content or "").strip()
                    or (f"收款 {amount_text} 元" if item.activity_type == "PAYMENT" and amount_text else "催收记录"),
                    note=_join_note_parts(
                        f"类型 {item.payment_nature}" if item.payment_nature else "",
                        f"入账账户 {item.receipt_account}" if item.receipt_account else "",
                        "预付" if item.is_prepay else "",
                        "已结清" if item.is_settlement else "",
                        (item.note or "").strip(),
                    ),
                    amount=float(item.amount) if item.activity_type == "PAYMENT" else None,
                    actor_username=(item.actor_username or "").strip(),
                    extra=f"下次跟进：{item.next_followup_at}" if item.next_followup_at else "",
                ),
            )
        )

    for item in execution_logs:
        timeline_rows.append(
            (
                item.occurred_at,
                30,
                int(item.id),
                CustomerTimelineEntryOut(
                    occurred_at=item.occurred_at,
                    source_type="EXECUTION_LOG",
                    source_id=item.id,
                    title=_execution_label(item.progress_type),
                    content=(item.content or "").strip() or "执行进度更新",
                    note=_join_note_parts(
                        f"下一步：{item.next_action}" if item.next_action else "",
                        f"目标完成：{item.due_date}" if item.due_date else "",
                        (item.note or "").strip(),
                    ),
                    actor_username=(item.actor_username or "").strip(),
                    extra="",
                ),
            )
        )

    for item in customer_events:
        timeline_rows.append(
            (
                item.occurred_at,
                20,
                int(item.id),
                CustomerTimelineEntryOut(
                    occurred_at=item.occurred_at,
                    source_type="CUSTOMER_EVENT",
                    source_id=item.id,
                    title=_timeline_event_label(item.event_type),
                    content=(item.content or "").strip() or "客户记录",
                    note=(item.note or "").strip(),
                    amount=float(item.amount) if item.amount is not None else None,
                    status=(item.status or "").strip(),
                    reminder_at=item.reminder_at,
                    completed_at=item.completed_at,
                    result=(item.result or "").strip(),
                    actor_username=(item.actor_username or "").strip(),
                    extra=_build_customer_event_extra(item),
                ),
            )
        )

    timeline_rows.sort(key=lambda item: (item[0], item[1], item[2]), reverse=True)
    return [item[3] for item in timeline_rows]


@router.get("", response_model=list[CustomerListOut])
def list_customers(
    keyword: Optional[str] = Query(default=None),
    sort_by: Optional[str] = Query(default=None),
    sort_order: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    accountant_user = aliased(User)
    responsible_user = aliased(User)
    stmt = (
        select(
            Customer,
            accountant_user.username,
            responsible_user.username,
            Lead.template_type,
            Lead.grade,
            Lead.region,
            Lead.country,
            Lead.contact_start_date,
            Lead.service_start_text,
            Lead.company_nature,
            Lead.service_mode,
            Lead.contact_wechat,
            Lead.other_contact,
            Lead.main_business,
            Lead.intro,
            Lead.fee_standard,
            Lead.first_billing_period,
            Lead.last_followup_date,
            Lead.reminder_value,
        )
        .outerjoin(accountant_user, Customer.assigned_accountant_id == accountant_user.id)
        .outerjoin(responsible_user, Customer.responsible_user_id == responsible_user.id)
        .join(Lead, Customer.source_lead_id == Lead.id)
        .where(active_filter(Customer), active_filter(Lead))
    )
    if keyword:
        key = f"%{keyword.strip()}%"
        stmt = stmt.where(
            or_(
                Customer.name.ilike(key),
                Customer.contact_name.ilike(key),
                Customer.phone.ilike(key),
                Customer.customer_code.ilike(key),
                accountant_user.username.ilike(key),
                responsible_user.username.ilike(key),
            )
        )
    stmt = _apply_customer_scope_stmt(stmt, db, current_user)
    stmt = _apply_customer_sort(stmt, sort_by, sort_order, accountant_username_column=accountant_user.username)

    rows = db.execute(stmt).all()
    result: list[CustomerListOut] = []
    for (
        customer,
        accountant_username,
        responsible_username,
        template_type,
        grade,
        region,
        country,
        contact_start_date,
        service_start_text,
        company_nature,
        service_mode,
        contact_wechat,
        other_contact,
        main_business,
        intro,
        fee_standard,
        first_billing_period,
        last_followup_date,
        reminder_value,
    ) in rows:
        source_area_display = country or region or ""
        source_service_start_display = service_start_text or (
            contact_start_date.isoformat() if contact_start_date else ""
        )
        result.append(
            CustomerListOut(
                id=customer.id,
                customer_code_seq=customer.customer_code_seq,
                customer_code_suffix=customer.customer_code_suffix or "",
                customer_code=customer.customer_code or _format_customer_code(customer.customer_code_seq, customer.customer_code_suffix),
                name=customer.name,
                contact_name=customer.contact_name,
                phone=customer.phone,
                status=customer.status,
                responsible_user_id=customer.responsible_user_id,
                responsible_username=responsible_username or "",
                assigned_accountant_id=customer.assigned_accountant_id,
                accountant_username=accountant_username or "",
                source_customer_id=customer.source_customer_id,
                source_lead_id=customer.source_lead_id,
                source_template_type=template_type or "",
                source_grade=grade or "",
                source_country=country or "",
                source_service_start_text=service_start_text or "",
                source_area_display=source_area_display,
                source_service_start_display=source_service_start_display,
                source_company_nature=company_nature or "",
                source_service_mode=service_mode or "",
                source_contact_wechat=contact_wechat or "",
                source_other_contact=other_contact or "",
                source_main_business=main_business or "",
                source_intro=intro or "",
                source_fee_standard=fee_standard or "",
                source_first_billing_period=first_billing_period or "",
                source_last_followup_date=last_followup_date,
                source_reminder_value=reminder_value or "",
                created_at=customer.created_at,
            )
        )
    return result


@router.get("/import-template", dependencies=[Depends(require_roles("OWNER", "ADMIN", "MANAGER"))])
def download_customer_import_template(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    content = build_customer_template_bytes()
    write_operation_log(
        db,
        actor_id=current_user.id,
        action="CUSTOMER_IMPORT_TEMPLATE_DOWNLOADED",
        entity_type="CUSTOMER_IMPORT",
        entity_id="template",
        detail="customer-import-template.xlsx",
    )
    db.commit()
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="customer-import-template.xlsx"'},
    )


@router.get("/export")
def export_customers(
    keyword: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    accountant_user = aliased(User)
    stmt = (
        select(Customer, accountant_user.username, Lead)
        .outerjoin(accountant_user, Customer.assigned_accountant_id == accountant_user.id)
        .join(Lead, Customer.source_lead_id == Lead.id)
        .where(active_filter(Customer), active_filter(Lead))
        .order_by(Customer.id.desc())
    )
    if keyword:
        key = f"%{keyword.strip()}%"
        stmt = stmt.where(
            or_(
                Customer.name.ilike(key),
                Customer.contact_name.ilike(key),
                Customer.phone.ilike(key),
                Customer.customer_code.ilike(key),
                accountant_user.username.ilike(key),
            )
        )
    stmt = _apply_customer_scope_stmt(stmt, db, current_user)

    export_rows = [
        _serialize_customer_export_row(customer, lead, accountant_username)
        for customer, accountant_username, lead in db.execute(stmt).all()
    ]
    content = build_customer_export_bytes(export_rows)
    write_operation_log(
        db,
        actor_id=current_user.id,
        action="CUSTOMERS_EXPORTED",
        entity_type="CUSTOMER",
        entity_id="export",
        detail=f"count={len(export_rows)},keyword={keyword or ''}",
    )
    db.commit()
    filename = f"customers-export-{date.today().isoformat()}.xlsx"
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post(
    "/import",
    response_model=CustomerImportResultOut,
    dependencies=[Depends(require_roles("OWNER", "ADMIN", "MANAGER"))],
)
async def import_customers(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    filename = (file.filename or "").strip()
    if not filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请先选择导入文件")
    if not filename.lower().endswith((".xlsx", ".csv")):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="仅支持 .xlsx 或 .csv 文件")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="导入文件为空")

    try:
        parsed_rows = parse_customer_import_file(filename, content)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if not parsed_rows:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="模板里没有可导入的数据行")

    created_count = 0
    updated_count = 0
    skipped_count = 0
    error_count = 0
    row_results: list[CustomerImportRowResultOut] = []

    for row_number, row in parsed_rows:
        company_name = _normalize_text(row.get("name", ""))
        try:
            with db.begin_nested():
                existing_customer = _find_customer_for_import(
                    db,
                    customer_id_text=row.get("customer_id", ""),
                    customer_code_text=row.get("customer_code", ""),
                )
                if existing_customer is not None:
                    _ensure_customer_access(existing_customer, current_user, db, for_write=True)
                    lead = db.execute(
                        select(Lead).where(Lead.id == existing_customer.source_lead_id, active_filter(Lead))
                    ).scalar_one_or_none()
                    if lead is None:
                        raise ValueError("来源线索不存在，无法更新该客户")

                    changed = False
                    imported_name = company_name
                    if imported_name and imported_name != existing_customer.name:
                        existing_customer.name = imported_name
                        lead.name = imported_name
                        for record in existing_customer.billing_records:
                            record.customer_name = imported_name
                        changed = True

                    imported_contact_name = _normalize_text(row.get("contact_name", ""))
                    if imported_contact_name and imported_contact_name != existing_customer.contact_name:
                        existing_customer.contact_name = imported_contact_name
                        lead.contact_name = imported_contact_name
                        changed = True

                    imported_phone = _normalize_text(row.get("phone", ""))
                    if imported_phone and imported_phone != existing_customer.phone:
                        existing_customer.phone = imported_phone
                        lead.phone = imported_phone
                        changed = True

                    imported_status = _normalize_text(row.get("status", "")).upper()
                    if imported_status:
                        if current_user.role == "MANAGER" and imported_status != existing_customer.status:
                            raise ValueError("部门经理不能通过导入修改客户状态")
                        if imported_status != existing_customer.status:
                            existing_customer.status = imported_status
                            changed = True

                    accountant_id = _resolve_import_accountant_id(
                        db,
                        current_user,
                        row.get("accountant_username", ""),
                        existing_customer=existing_customer,
                    )
                    if accountant_id != existing_customer.assigned_accountant_id:
                        existing_customer.assigned_accountant_id = accountant_id
                        existing_customer.responsible_user_id = accountant_id
                        changed = True

                    imported_code = _normalize_text(row.get("customer_code", "")).upper()
                    if imported_code:
                        seq, suffix = _parse_customer_code(imported_code)
                        normalized_code = _format_customer_code(seq, suffix)
                        duplicate = db.execute(
                            select(Customer).where(
                                Customer.customer_code == normalized_code,
                                Customer.id != existing_customer.id,
                                active_filter(Customer),
                            )
                        ).scalar_one_or_none()
                        if duplicate is not None:
                            raise ValueError(f"客户编号已被其他客户使用：{normalized_code}")
                        if existing_customer.customer_code and existing_customer.customer_code != normalized_code:
                            raise ValueError(
                                f"当前客户已有编号 {existing_customer.customer_code}，如需修改请单独处理"
                            )
                        if not existing_customer.customer_code:
                            existing_customer.customer_code_seq = seq
                            existing_customer.customer_code_suffix = suffix
                            existing_customer.customer_code = normalized_code
                            changed = True

                    text_field_pairs = [
                        ("lead_grade", "grade"),
                        ("lead_region", "region"),
                        ("lead_country", "country"),
                        ("lead_service_start_text", "service_start_text"),
                        ("lead_company_nature", "company_nature"),
                        ("lead_service_mode", "service_mode"),
                        ("lead_contact_wechat", "contact_wechat"),
                        ("lead_other_contact", "other_contact"),
                        ("lead_main_business", "main_business"),
                        ("lead_source", "source"),
                        ("lead_intro", "intro"),
                        ("lead_fee_standard", "fee_standard"),
                        ("lead_first_billing_period", "first_billing_period"),
                        ("lead_reminder_value", "reminder_value"),
                        ("lead_notes", "notes"),
                    ]
                    for _, field_name in text_field_pairs:
                        imported_value = _normalize_text(row.get(field_name, ""))
                        if not imported_value:
                            continue
                        current_value = _normalize_text(getattr(lead, field_name))
                        if imported_value != current_value:
                            setattr(lead, field_name, imported_value)
                            changed = True

                    imported_next_reminder = _normalize_text(row.get("next_reminder_at", ""))
                    if imported_next_reminder:
                        parsed_next_reminder = _parse_date_text(imported_next_reminder)
                        if parsed_next_reminder != lead.next_reminder_at:
                            lead.next_reminder_at = parsed_next_reminder
                            changed = True

                    if changed:
                        updated_count += 1
                        row_results.append(
                            CustomerImportRowResultOut(
                                row_number=row_number,
                                company_name=existing_customer.name,
                                action="UPDATED",
                                message="客户信息已更新",
                            )
                        )
                    else:
                        skipped_count += 1
                        row_results.append(
                            CustomerImportRowResultOut(
                                row_number=row_number,
                                company_name=existing_customer.name,
                                action="SKIPPED",
                                message="没有检测到变化，已跳过",
                            )
                        )
                    continue

                if not company_name:
                    raise ValueError("新增客户必须填写公司名称")
                contact_name = _normalize_text(row.get("contact_name", "")) or company_name
                phone = _normalize_text(row.get("phone", ""))
                source = _normalize_text(row.get("source", "")) or "Excel导入"
                intro = _normalize_text(row.get("intro", ""))
                accountant_id = _resolve_import_accountant_id(
                    db,
                    current_user,
                    row.get("accountant_username", ""),
                    existing_customer=None,
                )
                imported_code = _normalize_text(row.get("customer_code", "")).upper()
                if imported_code:
                    code_seq, code_suffix = _parse_customer_code(imported_code)
                else:
                    code_seq = _next_customer_code_seq(db)
                    code_suffix = _default_customer_code_suffix(source, intro)
                normalized_code = _format_customer_code(code_seq, code_suffix)
                duplicate_code = db.execute(
                    select(Customer).where(Customer.customer_code == normalized_code, active_filter(Customer))
                ).scalar_one_or_none()
                if duplicate_code is not None:
                    raise ValueError(f"客户编号已存在：{normalized_code}")

                parsed_service_date = _parse_date_text(row.get("service_start_text", ""))
                parsed_next_reminder = _parse_date_text(row.get("next_reminder_at", ""))

                lead = Lead(
                    template_type="CONVERSION",
                    name=company_name,
                    contact_name=contact_name,
                    phone=phone,
                    region=_normalize_text(row.get("region", "")),
                    country=_normalize_text(row.get("country", "")),
                    source=source,
                    contact_wechat=_normalize_text(row.get("contact_wechat", "")),
                    other_contact=_normalize_text(row.get("other_contact", "")),
                    contact_start_date=parsed_service_date or date.today(),
                    service_start_text=_normalize_text(row.get("service_start_text", "")),
                    company_nature=_normalize_text(row.get("company_nature", "")),
                    service_mode=_normalize_text(row.get("service_mode", "")),
                    main_business=_normalize_text(row.get("main_business", "")),
                    intro=intro,
                    fee_standard=_normalize_text(row.get("fee_standard", "")),
                    first_billing_period=_normalize_text(row.get("first_billing_period", "")),
                    status="CONVERTED",
                    next_reminder_at=parsed_next_reminder,
                    reminder_value=_normalize_text(row.get("reminder_value", "")),
                    notes=_normalize_text(row.get("notes", "")),
                    grade=_normalize_text(row.get("grade", "")),
                    owner_id=current_user.id,
                )
                db.add(lead)
                db.flush()

                customer = Customer(
                    name=company_name,
                    contact_name=contact_name,
                    phone=phone,
                    status=_normalize_text(row.get("status", "")).upper() or "ACTIVE",
                    responsible_user_id=accountant_id,
                    assigned_accountant_id=accountant_id,
                    customer_code_seq=code_seq,
                    customer_code_suffix=code_suffix,
                    customer_code=normalized_code,
                    source_lead_id=lead.id,
                )
                db.add(customer)
                db.flush()

                created_count += 1
                row_results.append(
                    CustomerImportRowResultOut(
                        row_number=row_number,
                        company_name=company_name,
                        action="CREATED",
                        message=f"客户已新增，编号 {normalized_code}",
                    )
                )
        except (HTTPException, ValueError) as exc:
            error_count += 1
            message = exc.detail if isinstance(exc, HTTPException) else str(exc)
            row_results.append(
                CustomerImportRowResultOut(
                    row_number=row_number,
                    company_name=company_name or f"第 {row_number} 行",
                    action="ERROR",
                    message=str(message),
                )
            )

    write_operation_log(
        db,
        actor_id=current_user.id,
        action="CUSTOMERS_IMPORTED",
        entity_type="CUSTOMER",
        entity_id=filename,
        detail=(
            f"created={created_count},updated={updated_count},"
            f"skipped={skipped_count},error={error_count}"
        ),
    )
    db.commit()
    return CustomerImportResultOut(
        created_count=created_count,
        updated_count=updated_count,
        skipped_count=skipped_count,
        error_count=error_count,
        rows=row_results,
    )


@router.get("/suggest", response_model=list[CustomerSuggestOut])
def suggest_customers(
    keyword: str = Query(default="", min_length=1),
    limit: int = Query(default=12, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    key = keyword.strip()
    if not key:
        return []
    stmt = (
        select(Customer)
        .where(active_filter(Customer))
        .where(
            or_(
                Customer.name.ilike(f"%{key}%"),
                Customer.contact_name.ilike(f"%{key}%"),
                Customer.phone.ilike(f"%{key}%"),
                Customer.customer_code.ilike(f"%{key}%"),
            )
        )
        .order_by(Customer.created_at.desc(), Customer.id.desc())
        .limit(limit)
    )
    stmt = _apply_customer_scope_stmt(stmt, db, current_user)
    rows = db.execute(stmt).scalars().all()
    return [
        CustomerSuggestOut(
            id=item.id,
            name=item.name,
            contact_name=item.contact_name,
            phone=item.phone,
            customer_code=item.customer_code or _format_customer_code(item.customer_code_seq, item.customer_code_suffix),
            label=" / ".join(
                [
                    part
                    for part in [
                        (item.customer_code or _format_customer_code(item.customer_code_seq, item.customer_code_suffix)),
                        item.name,
                        item.contact_name,
                        item.phone,
                    ]
                    if part
                ]
            ),
        )
        for item in rows
    ]


@router.get("/matters/summary", response_model=list[CustomerMatterSummaryOut])
def list_customer_matter_summaries(
    keyword: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = (
        select(Customer, Lead)
        .join(Lead, Customer.source_lead_id == Lead.id)
        .where(active_filter(Customer), active_filter(Lead))
        .order_by(Customer.id.desc())
    )
    if keyword:
        key = f"%{keyword.strip()}%"
        stmt = stmt.where(
            or_(
                Customer.name.ilike(key),
                Customer.contact_name.ilike(key),
                Customer.phone.ilike(key),
                Customer.customer_code.ilike(key),
                Lead.main_business.ilike(key),
            )
        )
    stmt = _apply_customer_scope_stmt(stmt, db, current_user)

    rows = db.execute(stmt).all()
    customer_ids = [customer.id for customer, _ in rows]
    event_rows = db.execute(
        select(CustomerTimelineEvent)
        .where(CustomerTimelineEvent.customer_id.in_(customer_ids))
        .order_by(CustomerTimelineEvent.occurred_at.desc(), CustomerTimelineEvent.id.desc())
    ).scalars().all() if customer_ids else []

    event_map: dict[int, list[CustomerTimelineEvent]] = {}
    for item in event_rows:
        event_map.setdefault(item.customer_id, []).append(item)

    result: list[CustomerMatterSummaryOut] = []
    for customer, lead in rows:
        events = event_map.get(customer.id, [])
        open_events = [item for item in events if (item.status or "").upper() == "OPEN"]
        latest_reminder = max((item.reminder_at for item in open_events if item.reminder_at is not None), default=None)
        latest_progress_row = events[0] if events else None
        latest_progress = ""
        if latest_progress_row is not None:
            latest_progress = (latest_progress_row.result or "").strip() or (latest_progress_row.content or "").strip()
        result.append(
            CustomerMatterSummaryOut(
                customer_id=customer.id,
                customer_name=customer.name,
                customer_code=customer.customer_code or _format_customer_code(customer.customer_code_seq, customer.customer_code_suffix),
                customer_contact_name=customer.contact_name,
                service_start_display=_customer_service_start_display(lead),
                current_service_summary=(lead.main_business or "").strip() or (lead.fee_standard or "").strip() or "-",
                open_item_count=len(open_events),
                latest_reminder_at=latest_reminder,
                latest_progress=latest_progress,
            )
        )
    return result


@router.get("/{customer_id}", response_model=CustomerDetailOut)
def get_customer_detail(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    customer = _get_customer_or_404(db, customer_id)
    _ensure_customer_access(customer, current_user, db)

    lead = (
        db.execute(
            select(Lead).options(selectinload(Lead.customer)).where(Lead.id == customer.source_lead_id, active_filter(Lead))
        )
        .scalar_one_or_none()
    )
    if lead is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source lead not found")

    followups = db.execute(
        select(LeadFollowup)
        .options(selectinload(LeadFollowup.creator))
        .where(LeadFollowup.lead_id == lead.id)
        .order_by(LeadFollowup.followup_at.desc(), LeadFollowup.id.desc())
    ).scalars().all()

    timeline = _build_customer_timeline(db, customer, lead)

    return CustomerDetailOut(
        id=customer.id,
        customer_code_seq=customer.customer_code_seq,
        customer_code_suffix=customer.customer_code_suffix or "",
        customer_code=customer.customer_code or _format_customer_code(customer.customer_code_seq, customer.customer_code_suffix),
        name=customer.name,
        contact_name=customer.contact_name,
        phone=customer.phone,
        status=customer.status,
        responsible_user_id=customer.responsible_user_id,
        responsible_username=customer.responsible_username,
        assigned_accountant_id=customer.assigned_accountant_id,
        accountant_username=customer.accountant_username,
        source_customer_id=customer.source_customer_id,
        source_lead_id=customer.source_lead_id,
        created_at=customer.created_at,
        lead=lead,
        followups=followups,
        timeline=timeline,
    )


@router.delete(
    "/{customer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles("OWNER", "ADMIN"))],
)
def delete_customer(
    customer_id: int,
    confirm_name: str = Query(default=""),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    customer = _get_customer_or_404(db, customer_id)

    expected_name = (customer.name or "").strip() or (customer.contact_name or "").strip() or f"客户#{customer.id}"
    if (confirm_name or "").strip() != expected_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="删除确认名称不匹配")
    blockers = _build_customer_delete_blockers(db, customer)
    if blockers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "reason": "DEPENDENCY_BLOCKED",
                "message": "该客户还有关联记录，需先处理这些记录后才能删除。",
                "blockers": [item.model_dump() for item in blockers],
            },
        )

    for item in db.execute(
        select(AddressResourceCompany).where(
            AddressResourceCompany.customer_id == customer.id,
            active_filter(AddressResourceCompany),
        )
    ).scalars().all():
        if not (item.company_name or "").strip():
            item.company_name = customer.name

    mark_deleted(customer, current_user.id)
    write_operation_log(
        db,
        actor_id=current_user.id,
        action="CUSTOMER_DELETED",
        entity_type="CUSTOMER",
        entity_id=customer.id,
        detail=f"name={expected_name}",
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(
    "/{customer_id}/timeline-events/{event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles("OWNER", "ADMIN"))],
)
def delete_customer_timeline_event(
    customer_id: int,
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    customer = _get_customer_or_404(db, customer_id)
    _ensure_customer_access(customer, current_user, db, for_write=True)

    event = db.execute(
        select(CustomerTimelineEvent).where(
            CustomerTimelineEvent.id == event_id,
            CustomerTimelineEvent.customer_id == customer_id,
        )
    ).scalar_one_or_none()
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="客户记录不存在")

    db.delete(event)
    write_operation_log(
        db,
        actor_id=current_user.id,
        action="CUSTOMER_TIMELINE_EVENT_DELETED",
        entity_type="CUSTOMER_TIMELINE",
        entity_id=event.id,
        detail=f"customer_id={customer.id},content={(event.content or '').strip()}",
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{customer_id}/timeline-events",
    response_model=CustomerTimelineEventOut,
    status_code=status.HTTP_201_CREATED,
)
def create_customer_timeline_event(
    customer_id: int,
    payload: CustomerTimelineEventCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    customer = _get_customer_or_404(db, customer_id)
    _ensure_customer_access(customer, current_user, db, for_write=True)

    content = (payload.content or "").strip()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Content is required")

    event_status = _normalize_customer_event_status(payload.status)
    reminder_at = payload.reminder_at
    completed_at = payload.completed_at
    result = (payload.result or "").strip()

    if event_status == "OPEN" and reminder_at is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="待跟进记录必须设置提醒日期")
    if event_status == "DONE" and completed_at is None:
        completed_at = payload.occurred_at
    if event_status == "NOTE":
        reminder_at = None
        completed_at = None
        result = ""

    event = CustomerTimelineEvent(
        customer_id=customer.id,
        occurred_at=payload.occurred_at,
        event_type=(payload.event_type or "COMMUNICATION").strip().upper(),
        status=event_status,
        reminder_at=reminder_at,
        completed_at=completed_at,
        content=content,
        note=(payload.note or "").strip(),
        result=result,
        amount=payload.amount,
        actor_id=current_user.id,
    )
    db.add(event)
    write_operation_log(
        db,
        actor_id=current_user.id,
        action="CUSTOMER_TIMELINE_EVENT_CREATED",
        entity_type="CUSTOMER_TIMELINE",
        entity_id=customer.id,
        detail=f"type={event.event_type},occurred_at={event.occurred_at}",
    )
    db.commit()
    db.refresh(event)
    return event


@router.patch(
    "/{customer_id}/timeline-events/{event_id}",
    response_model=CustomerTimelineEventOut,
)
def update_customer_timeline_event(
    customer_id: int,
    event_id: int,
    payload: CustomerTimelineEventUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    customer = _get_customer_or_404(db, customer_id)
    _ensure_customer_access(customer, current_user, db, for_write=True)

    event = db.execute(
        select(CustomerTimelineEvent).where(
            CustomerTimelineEvent.id == event_id,
            CustomerTimelineEvent.customer_id == customer_id,
        )
    ).scalar_one_or_none()
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="客户记录不存在")

    update_data = payload.model_dump(exclude_unset=True)
    if "event_type" in update_data:
        event.event_type = (payload.event_type or event.event_type).strip().upper()
    if "occurred_at" in update_data:
        event.occurred_at = payload.occurred_at
    if "content" in update_data:
        content = (payload.content or "").strip()
        if not content:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Content is required")
        event.content = content
    if "note" in update_data:
        event.note = (payload.note or "").strip()
    if "result" in update_data:
        event.result = (payload.result or "").strip()
    if "amount" in update_data:
        event.amount = payload.amount
    if "reminder_at" in update_data:
        event.reminder_at = payload.reminder_at
    if "completed_at" in update_data:
        event.completed_at = payload.completed_at
    if "status" in update_data:
        event.status = _normalize_customer_event_status(payload.status or event.status)

    if event.status == "OPEN" and event.reminder_at is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="待跟进记录必须设置提醒日期")
    if event.status == "DONE" and event.completed_at is None:
        event.completed_at = date.today()
    if event.status == "NOTE":
        event.reminder_at = None
        event.completed_at = None
        event.result = ""

    write_operation_log(
        db,
        actor_id=current_user.id,
        action="CUSTOMER_TIMELINE_EVENT_UPDATED",
        entity_type="CUSTOMER_TIMELINE",
        entity_id=customer.id,
        detail=f"event_id={event.id},status={event.status}",
    )
    db.commit()
    db.refresh(event)
    return event


@router.post(
    "/{customer_id}/timeline-templates/{template_key}",
    response_model=list[CustomerTimelineEventOut],
    status_code=status.HTTP_201_CREATED,
)
def apply_customer_timeline_template(
    customer_id: int,
    template_key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    customer = _get_customer_or_404(db, customer_id)
    _ensure_customer_access(customer, current_user, db, for_write=True)

    lead = db.execute(select(Lead).where(Lead.id == customer.source_lead_id, active_filter(Lead))).scalar_one_or_none()
    if lead is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source lead not found")

    normalized_key = (template_key or "").strip().lower()
    if normalized_key != "hk-company":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不支持的客户模板")

    candidates = _build_hk_company_template_events(customer, lead, current_user.id)
    existing_rows = db.execute(
        select(CustomerTimelineEvent).where(
            CustomerTimelineEvent.customer_id == customer.id,
            CustomerTimelineEvent.template_key == "HK_COMPANY",
        )
    ).scalars().all()
    existing_keys = {
        (item.template_key or "", item.content or "", item.reminder_at.isoformat() if item.reminder_at else "")
        for item in existing_rows
    }

    created: list[CustomerTimelineEvent] = []
    for item in candidates:
        dedupe_key = (
            item.template_key or "",
            item.content or "",
            item.reminder_at.isoformat() if item.reminder_at else "",
        )
        if dedupe_key in existing_keys:
            continue
        db.add(item)
        created.append(item)

    if not created:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="香港公司模板已应用到当前周期")

    write_operation_log(
        db,
        actor_id=current_user.id,
        action="CUSTOMER_TIMELINE_TEMPLATE_APPLIED",
        entity_type="CUSTOMER",
        entity_id=customer.id,
        detail=f"template=HK_COMPANY,count={len(created)}",
    )
    db.commit()
    for item in created:
        db.refresh(item)
    return created


@router.patch(
    "/{customer_id}",
    response_model=CustomerDetailOut,
)
def update_customer(
    customer_id: int,
    payload: CustomerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    customer = _get_customer_or_404(db, customer_id)
    _ensure_customer_access(customer, current_user, db, for_write=True)

    lead = db.execute(select(Lead).where(Lead.id == customer.source_lead_id, active_filter(Lead))).scalar_one_or_none()
    if lead is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source lead not found")

    if payload.assigned_accountant_id is not None:
        if current_user.role == "ACCOUNTANT":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        accountant = db.execute(select(User).where(User.id == payload.assigned_accountant_id)).scalar_one_or_none()
        if accountant is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Assigned accountant not found")
        if accountant.role != "ACCOUNTANT":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Assigned user must be ACCOUNTANT")
        if current_user.role == "MANAGER":
            managed_ids = set(get_manager_subordinate_ids(db, current_user.id))
            if accountant.id not in managed_ids:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="不能把客户改派给非直属下属")
        customer.assigned_accountant_id = accountant.id

    if payload.name is not None:
        customer.name = payload.name
        lead.name = payload.name
        for record in customer.billing_records:
            record.customer_name = payload.name
    if payload.contact_name is not None:
        customer.contact_name = payload.contact_name
        lead.contact_name = payload.contact_name
    if payload.phone is not None:
        customer.phone = payload.phone
        lead.phone = payload.phone
    if payload.status is not None:
        if current_user.role in {"ACCOUNTANT", "MANAGER"}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        customer.status = payload.status

    if payload.lead_grade is not None:
        lead.grade = payload.lead_grade
    if payload.lead_contact_wechat is not None:
        lead.contact_wechat = payload.lead_contact_wechat
    if payload.lead_fax is not None:
        lead.fax = payload.lead_fax
    if payload.lead_other_contact is not None:
        lead.other_contact = payload.lead_other_contact
    if payload.lead_region is not None:
        lead.region = payload.lead_region
    if payload.lead_country is not None:
        lead.country = payload.lead_country
    if payload.lead_service_start_text is not None:
        lead.service_start_text = payload.lead_service_start_text
    if payload.lead_company_nature is not None:
        lead.company_nature = payload.lead_company_nature
    if payload.lead_service_mode is not None:
        lead.service_mode = payload.lead_service_mode
    if payload.lead_fee_standard is not None:
        lead.fee_standard = payload.lead_fee_standard
    if payload.lead_first_billing_period is not None:
        lead.first_billing_period = payload.lead_first_billing_period
    if payload.lead_reminder_value is not None:
        lead.reminder_value = payload.lead_reminder_value
    if payload.lead_next_reminder_at is not None:
        lead.next_reminder_at = payload.lead_next_reminder_at
    if payload.lead_source is not None:
        lead.source = payload.lead_source
    if payload.lead_main_business is not None:
        lead.main_business = payload.lead_main_business
    if payload.lead_intro is not None:
        lead.intro = payload.lead_intro
    if payload.lead_notes is not None:
        lead.notes = payload.lead_notes

    write_operation_log(
        db,
        actor_id=current_user.id,
        action="CUSTOMER_UPDATED",
        entity_type="CUSTOMER",
        entity_id=customer.id,
        detail=f"name={customer.name}",
    )
    db.commit()
    return get_customer_detail(customer_id=customer_id, db=db, current_user=current_user)
