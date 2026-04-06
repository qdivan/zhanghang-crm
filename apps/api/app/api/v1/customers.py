from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

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
    CustomerListOut,
    CustomerTimelineEntryOut,
    CustomerTimelineEventCreate,
    CustomerTimelineEventOut,
    CustomerTimelineEventUpdate,
    CustomerUpdate,
)
from app.services.audit import write_operation_log
from app.services.data_access import has_module_read_grant
from app.services.org_scope import get_manager_subordinate_ids
from app.services.soft_delete import active_filter, mark_deleted

router = APIRouter(prefix="/customers", tags=["customers"])


def _get_customer_or_404(db: Session, customer_id: int) -> Customer:
    customer = db.execute(select(Customer).where(Customer.id == customer_id, active_filter(Customer))).scalar_one_or_none()
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return customer


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
        if customer.assigned_accountant_id in set(get_manager_subordinate_ids(db, current_user.id)):
            return
    else:
        if customer.assigned_accountant_id == current_user.id:
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
    accountant = db.execute(select(User).where(User.id == customer.assigned_accountant_id)).scalar_one_or_none()

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
                    content=f"已转入客户列表，并分配会计 {accountant.username if accountant else customer.assigned_accountant_id}",
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    has_customer_read_grant = False
    if current_user.role == "ACCOUNTANT":
        has_customer_read_grant = has_module_read_grant(db, current_user.id, "CUSTOMER")

    stmt = (
        select(
            Customer,
            User.username,
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
        .join(User, Customer.assigned_accountant_id == User.id)
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
                User.username.ilike(key),
            )
        )
    if current_user.role == "MANAGER":
        managed_ids = get_manager_subordinate_ids(db, current_user.id)
        stmt = stmt.where(Customer.assigned_accountant_id.in_(managed_ids))
    elif current_user.role == "ACCOUNTANT" and not has_customer_read_grant:
        stmt = stmt.where(Customer.assigned_accountant_id == current_user.id)

    rows = db.execute(stmt).all()
    result: list[CustomerListOut] = []
    for (
        customer,
        accountant_username,
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
                name=customer.name,
                contact_name=customer.contact_name,
                phone=customer.phone,
                status=customer.status,
                assigned_accountant_id=customer.assigned_accountant_id,
                accountant_username=accountant_username,
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

    accountant = db.execute(select(User).where(User.id == customer.assigned_accountant_id)).scalar_one_or_none()
    accountant_username = accountant.username if accountant else ""
    timeline = _build_customer_timeline(db, customer, lead)

    return CustomerDetailOut(
        id=customer.id,
        name=customer.name,
        contact_name=customer.contact_name,
        phone=customer.phone,
        status=customer.status,
        assigned_accountant_id=customer.assigned_accountant_id,
        accountant_username=accountant_username,
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

    billing_count = (
        db.execute(
            select(func.count(BillingRecord.id)).where(BillingRecord.customer_id == customer.id, active_filter(BillingRecord))
        ).scalar()
        or 0
    )
    if billing_count > 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Customer has billing records, cannot delete")

    payment_count = (
        db.execute(select(func.count(BillingPayment.id)).where(BillingPayment.customer_id == customer.id)).scalar() or 0
    )
    if payment_count > 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Customer has payment records, cannot delete")

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
