from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models import BillingRecord, Customer, Lead, LeadFollowup, User
from app.schemas.lead import (
    ConvertLeadRequest,
    ConvertLeadResponse,
    LeadCreate,
    LeadFollowupCreate,
    LeadFollowupOut,
    LeadOut,
    LeadUpdate,
)
from app.services.audit import write_operation_log
from app.services.data_access import has_module_read_grant
from app.services.org_scope import get_manager_subordinate_ids
from app.services.soft_delete import active_filter, deleted_filter, mark_deleted, restore_deleted

router = APIRouter(prefix="/leads", tags=["leads"])

GRADE_REMINDER_MAP = {
    "已签合同/待交费": "1天",
    "待下单": "3天",
    "意向中": "7天",
    "放弃": "不跟进",
}

REMINDER_DAY_MAP = {
    "1天": 1,
    "3天": 3,
    "7天": 7,
    "不跟进": None,
}

CUSTOMER_CODE_SUFFIX_MAP = {
    "SALLY直播": "S",
    "SALLY LIVE": "S",
    "麦总": "M",
}


def _get_lead_or_404(db: Session, lead_id: int) -> Lead:
    lead = db.execute(select(Lead).where(Lead.id == lead_id, active_filter(Lead))).scalar_one_or_none()
    if lead is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    return lead


def _default_reminder_value_for_grade(grade: str) -> str:
    return GRADE_REMINDER_MAP.get((grade or "").strip(), "")


def _default_customer_code_suffix(source: str, intro: str) -> str:
    source_key = (source or "").strip()
    intro_key = (intro or "").strip()
    for candidate in [source_key, intro_key]:
        if not candidate:
            continue
        upper_key = candidate.upper()
        if upper_key in CUSTOMER_CODE_SUFFIX_MAP:
            return CUSTOMER_CODE_SUFFIX_MAP[upper_key]
        if candidate in CUSTOMER_CODE_SUFFIX_MAP:
            return CUSTOMER_CODE_SUFFIX_MAP[candidate]
    return "A"


def _format_customer_code(seq: Optional[int], suffix: str) -> str:
    if not seq:
        return ""
    postfix = (suffix or "").strip().upper()
    base = str(int(seq)).zfill(4)
    return f"{base}{postfix}" if postfix else base


def _next_customer_code_seq(db: Session) -> int:
    current_max = db.execute(select(func.max(Customer.customer_code_seq))).scalar() or 0
    return int(current_max) + 1


def _next_reminder_date(base_date: Optional[date], reminder_value: str) -> Optional[date]:
    if base_date is None:
        return None
    days = REMINDER_DAY_MAP.get((reminder_value or "").strip())
    if days is None:
        return None
    return base_date + timedelta(days=int(days))


def _ensure_lead_access(lead: Lead, current_user: User, db: Session, *, for_write: bool = False) -> None:
    if current_user.role not in {"ACCOUNTANT", "MANAGER"}:
        return
    if current_user.role == "MANAGER":
        managed_ids = set(get_manager_subordinate_ids(db, current_user.id))
        if lead.owner_id in managed_ids:
            return
        if lead.customer is not None and not lead.customer.is_deleted and lead.customer.assigned_accountant_id in managed_ids:
            return
        if lead.related_customer_id is not None:
            related_customer_assignee = db.execute(
                select(Customer.assigned_accountant_id).where(
                    Customer.id == lead.related_customer_id,
                    active_filter(Customer),
                )
            ).scalar_one_or_none()
            if related_customer_assignee in managed_ids:
                return
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to this lead")

    if lead.owner_id == current_user.id:
        return
    # 转化后的客户，允许被分配的会计继续写跟进
    if lead.customer is not None and not lead.customer.is_deleted and lead.customer.assigned_accountant_id == current_user.id:
        return
    if lead.related_customer_id is not None:
        related_customer_assignee = db.execute(
            select(Customer.assigned_accountant_id).where(
                Customer.id == lead.related_customer_id,
                active_filter(Customer),
            )
        ).scalar_one_or_none()
        if related_customer_assignee == current_user.id:
            return
        if (
            not for_write
            and related_customer_assignee is not None
            and has_module_read_grant(db, current_user.id, "CUSTOMER")
        ):
            return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to this lead")


def _apply_lead_scope(stmt, current_user: User, db: Session):
    stmt = stmt.where(active_filter(Lead))
    if current_user.role == "MANAGER":
        managed_ids = get_manager_subordinate_ids(db, current_user.id)
        return stmt.where(
            or_(
                Lead.owner_id.in_(managed_ids),
                Lead.customer.has(and_(active_filter(Customer), Customer.assigned_accountant_id.in_(managed_ids))),
            )
        )
    if current_user.role == "ACCOUNTANT":
        return stmt.where(
            or_(
                Lead.owner_id == current_user.id,
                Lead.customer.has(and_(active_filter(Customer), Customer.assigned_accountant_id == current_user.id)),
            )
        )
    return stmt


@router.get("", response_model=list[LeadOut])
def list_leads(
    keyword: Optional[str] = Query(default=None),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    owner_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Lead).options(selectinload(Lead.customer)).order_by(Lead.id.desc())
    if keyword:
        key = f"%{keyword.strip()}%"
        stmt = stmt.where(
            or_(
                Lead.name.ilike(key),
                Lead.contact_name.ilike(key),
                Lead.phone.ilike(key),
            )
        )
    if status_filter:
        stmt = stmt.where(Lead.status == status_filter)
    if owner_id:
        stmt = stmt.where(Lead.owner_id == owner_id)
    stmt = _apply_lead_scope(stmt, current_user, db)

    return db.execute(stmt).scalars().all()


@router.get("/intro-options", response_model=list[str])
def list_lead_intro_options(
    q: Optional[str] = Query(default=None),
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = (
        select(Lead.intro, func.max(Lead.id).label("latest_id"))
        .where(func.trim(Lead.intro) != "", active_filter(Lead))
        .group_by(Lead.intro)
        .order_by(func.max(Lead.id).desc())
        .limit(limit)
    )
    if q:
        keyword = f"%{q.strip()}%"
        stmt = stmt.where(Lead.intro.ilike(keyword))
    stmt = _apply_lead_scope(stmt, current_user, db)
    rows = db.execute(stmt).all()
    return [str(intro).strip() for intro, _ in rows if str(intro).strip()]


@router.get("/source-options", response_model=list[str])
def list_lead_source_options(
    q: Optional[str] = Query(default=None),
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = (
        select(Lead.source, func.max(Lead.id).label("latest_id"))
        .where(func.trim(Lead.source) != "", active_filter(Lead))
        .group_by(Lead.source)
        .order_by(func.max(Lead.id).desc())
        .limit(limit)
    )
    if q:
        keyword = f"%{q.strip()}%"
        stmt = stmt.where(Lead.source.ilike(keyword))
    stmt = _apply_lead_scope(stmt, current_user, db)
    rows = db.execute(stmt).all()
    return [str(source).strip() for source, _ in rows if str(source).strip()]


@router.get("/{lead_id}", response_model=LeadOut)
def get_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    lead = (
        db.execute(select(Lead).options(selectinload(Lead.customer)).where(Lead.id == lead_id, active_filter(Lead)))
        .scalar_one_or_none()
    )
    if lead is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    _ensure_lead_access(lead, current_user, db)
    return lead


@router.post("", response_model=LeadOut, status_code=status.HTTP_201_CREATED)
def create_lead(
    payload: LeadCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    related_customer = None
    if current_user.role == "ACCOUNTANT":
        target_owner_id = current_user.id
    elif current_user.role == "MANAGER":
        target_owner_id = payload.owner_id or current_user.id
    else:
        target_owner_id = payload.owner_id or current_user.id

    owner = db.execute(select(User).where(User.id == target_owner_id)).scalar_one_or_none()
    if owner is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Owner not found")
    if current_user.role == "MANAGER":
        managed_ids = set(get_manager_subordinate_ids(db, current_user.id))
        if target_owner_id != current_user.id and target_owner_id not in managed_ids:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只能把线索分配给自己或直属下属")

    related_customer_id = payload.related_customer_id
    if related_customer_id is not None:
        related_customer = db.execute(
            select(Customer)
            .options(selectinload(Customer.source_lead))
            .where(Customer.id == related_customer_id, active_filter(Customer))
        ).scalar_one_or_none()
        if related_customer is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Related customer not found")
        if current_user.role == "ACCOUNTANT":
            can_link_related_customer = (
                related_customer.assigned_accountant_id == current_user.id
                or has_module_read_grant(db, current_user.id, "CUSTOMER")
            )
            if not can_link_related_customer:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No access to related customer",
                )
        if current_user.role == "MANAGER":
            managed_ids = set(get_manager_subordinate_ids(db, current_user.id))
            if related_customer.assigned_accountant_id not in managed_ids:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No access to related customer",
                )

    normalized_name = (payload.name or "").strip() or (payload.contact_name or "").strip()
    if not normalized_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="联系人不能为空")
    normalized_phone = (payload.phone or "").strip()
    normalized_source = (payload.source or "").strip()
    if not normalized_source:
        normalized_source = "老客户二次开发" if payload.template_type == "REDEVELOP" else "Sally直播"
    normalized_intro = (payload.intro or "").strip()
    if (
        not normalized_intro
        and payload.template_type == "REDEVELOP"
        and related_customer is not None
        and related_customer.source_lead is not None
    ):
        normalized_intro = (related_customer.source_lead.intro or "").strip()

    contact_start_date = payload.contact_start_date
    if contact_start_date is None and payload.template_type != "FOLLOWUP":
        contact_start_date = date.today()

    reminder_value = (payload.reminder_value or "").strip() or _default_reminder_value_for_grade(payload.grade)
    next_reminder_at = payload.next_reminder_at or _next_reminder_date(contact_start_date, reminder_value)

    lead = Lead(
        template_type=payload.template_type,
        name=normalized_name,
        grade=payload.grade,
        contact_name=payload.contact_name.strip(),
        phone=normalized_phone,
        region=payload.region,
        country=payload.country,
        source=normalized_source,
        contact_wechat=payload.contact_wechat,
        fax=payload.fax,
        other_contact=payload.other_contact,
        contact_start_date=contact_start_date,
        service_start_text=payload.service_start_text,
        company_nature=payload.company_nature,
        service_mode=payload.service_mode,
        main_business=payload.main_business.strip(),
        intro=normalized_intro,
        fee_standard=payload.fee_standard,
        first_billing_period=payload.first_billing_period,
        reserve_2=payload.reserve_2,
        reserve_3=payload.reserve_3,
        reserve_4=payload.reserve_4,
        status="NEW",
        next_reminder_at=next_reminder_at,
        reminder_value=reminder_value,
        notes=payload.notes,
        related_customer_id=related_customer_id,
        owner_id=target_owner_id,
    )
    db.add(lead)
    write_operation_log(
        db,
        actor_id=current_user.id,
        action="LEAD_CREATED",
        entity_type="LEAD",
        entity_id=lead.name,
        detail=(
            f"template={lead.template_type},owner={lead.owner_id},"
            f"related_customer_id={lead.related_customer_id or ''}"
        ),
    )
    db.commit()
    db.refresh(lead)
    return lead


@router.patch("/{lead_id}", response_model=LeadOut)
def update_lead(
    lead_id: int,
    payload: LeadUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    lead = _get_lead_or_404(db, lead_id)
    _ensure_lead_access(lead, current_user, db, for_write=True)

    if payload.name is not None:
        lead.name = payload.name
    if payload.contact_name is not None:
        lead.contact_name = payload.contact_name
    if payload.phone is not None:
        lead.phone = payload.phone
    if payload.status is not None:
        lead.status = payload.status
    if payload.template_type is not None:
        lead.template_type = payload.template_type
    if payload.grade is not None:
        lead.grade = payload.grade
    if payload.region is not None:
        lead.region = payload.region
    if payload.country is not None:
        lead.country = payload.country
    if payload.source is not None:
        lead.source = payload.source
    if payload.contact_wechat is not None:
        lead.contact_wechat = payload.contact_wechat
    if payload.fax is not None:
        lead.fax = payload.fax
    if payload.other_contact is not None:
        lead.other_contact = payload.other_contact
    if payload.contact_start_date is not None:
        lead.contact_start_date = payload.contact_start_date
    if payload.service_start_text is not None:
        lead.service_start_text = payload.service_start_text
    if payload.company_nature is not None:
        lead.company_nature = payload.company_nature
    if payload.service_mode is not None:
        lead.service_mode = payload.service_mode
    if payload.main_business is not None:
        lead.main_business = payload.main_business
    if payload.intro is not None:
        lead.intro = payload.intro
    if payload.fee_standard is not None:
        lead.fee_standard = payload.fee_standard
    if payload.first_billing_period is not None:
        lead.first_billing_period = payload.first_billing_period
    if payload.reserve_2 is not None:
        lead.reserve_2 = payload.reserve_2
    if payload.reserve_3 is not None:
        lead.reserve_3 = payload.reserve_3
    if payload.reserve_4 is not None:
        lead.reserve_4 = payload.reserve_4
    if payload.next_reminder_at is not None:
        lead.next_reminder_at = payload.next_reminder_at
    if payload.reminder_value is not None:
        lead.reminder_value = payload.reminder_value
    if payload.notes is not None:
        lead.notes = payload.notes
    if payload.related_customer_id is not None:
        related_customer = db.execute(select(Customer).where(Customer.id == payload.related_customer_id)).scalar_one_or_none()
        if related_customer is not None and related_customer.is_deleted:
            related_customer = None
        if related_customer is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Related customer not found")
        lead.related_customer_id = related_customer.id

    lead.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(lead)
    return lead


@router.delete(
    "/{lead_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles("OWNER", "ADMIN"))],
)
def delete_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    lead = _get_lead_or_404(db, lead_id)
    if lead.status == "CONVERTED" or lead.customer_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该线索已转化，请先撤销转化再删除",
        )

    mark_deleted(lead, current_user.id)
    write_operation_log(
        db,
        actor_id=current_user.id,
        action="LEAD_DELETED",
        entity_type="LEAD",
        entity_id=lead.id,
        detail=f"name={(lead.name or '').strip() or (lead.contact_name or '').strip()}",
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{lead_id}/followups", response_model=LeadFollowupOut, status_code=status.HTTP_201_CREATED)
def create_followup(
    lead_id: int,
    payload: LeadFollowupCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    lead = _get_lead_or_404(db, lead_id)
    _ensure_lead_access(lead, current_user, db, for_write=True)

    grade = (payload.grade or "").strip() or (lead.grade or "").strip()
    reminder_value = (payload.reminder_value or "").strip() or _default_reminder_value_for_grade(grade) or (
        lead.reminder_value or ""
    ).strip()
    next_reminder_at = payload.next_reminder_at
    if next_reminder_at is None:
        next_reminder_at = _next_reminder_date(payload.followup_at, reminder_value)

    followup = LeadFollowup(
        lead_id=lead_id,
        followup_at=payload.followup_at,
        feedback=payload.feedback,
        next_reminder_at=next_reminder_at,
        notes=payload.notes,
        created_by=current_user.id,
    )
    lead.last_feedback = payload.feedback
    lead.grade = grade
    lead.next_reminder_at = next_reminder_at
    lead.last_followup_date = payload.followup_at
    lead.reminder_value = reminder_value
    if lead.status != "CONVERTED":
        if grade == "放弃" or reminder_value == "不跟进":
            lead.status = "LOST"
        else:
            lead.status = "FOLLOWING"
    lead.updated_at = datetime.utcnow()

    db.add(followup)
    write_operation_log(
        db,
        actor_id=current_user.id,
        action="LEAD_FOLLOWUP_CREATED",
        entity_type="LEAD",
        entity_id=lead.id,
        detail=f"followup_at={payload.followup_at},grade={lead.grade},reminder_value={lead.reminder_value}",
    )
    db.commit()
    db.refresh(followup)
    return followup


@router.get("/{lead_id}/followups", response_model=list[LeadFollowupOut])
def list_followups(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    lead = _get_lead_or_404(db, lead_id)
    _ensure_lead_access(lead, current_user, db)

    stmt = (
        select(LeadFollowup)
        .where(LeadFollowup.lead_id == lead_id)
        .order_by(LeadFollowup.followup_at.desc(), LeadFollowup.id.desc())
    )
    return db.execute(stmt).scalars().all()


@router.post(
    "/{lead_id}/convert",
    response_model=ConvertLeadResponse,
    dependencies=[Depends(require_roles("OWNER", "MANAGER"))],
)
def convert_lead(
    lead_id: int,
    payload: ConvertLeadRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    lead = _get_lead_or_404(db, lead_id)
    _ensure_lead_access(lead, current_user, db, for_write=True)
    if lead.status == "CONVERTED":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Lead already converted")

    requested_name = (payload.customer_name or "").strip()
    requested_contact_name = (payload.customer_contact_name or "").strip()
    requested_phone = (payload.customer_phone or "").strip()
    requested_code_seq = payload.customer_code_seq
    requested_code_suffix = (payload.customer_code_suffix or "").strip().upper()
    conversion_mode = (payload.conversion_mode or "NEW_CUSTOMER_LINKED").strip().upper()
    if conversion_mode not in {"NEW_CUSTOMER_LINKED", "REUSE_CUSTOMER"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid conversion mode")
    if conversion_mode == "REUSE_CUSTOMER" and lead.related_customer_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前线索不能复用原客户")

    customer: Customer
    assigned_accountant_id = payload.accountant_id
    related_customer: Optional[Customer] = None
    if lead.related_customer_id is not None:
        related_customer = db.execute(
            select(Customer).where(Customer.id == lead.related_customer_id, active_filter(Customer))
        ).scalar_one_or_none()
        if related_customer is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Related customer not found")
        if assigned_accountant_id is None:
            assigned_accountant_id = related_customer.assigned_accountant_id
    if assigned_accountant_id is None:
        owner = db.execute(select(User).where(User.id == lead.owner_id)).scalar_one_or_none()
        if owner is not None and owner.role == "ACCOUNTANT":
            assigned_accountant_id = owner.id
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="accountant_id is required",
            )

    accountant = db.execute(select(User).where(User.id == assigned_accountant_id)).scalar_one_or_none()
    if accountant is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Assigned accountant not found")
    if accountant.role != "ACCOUNTANT":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Assigned user must be ACCOUNTANT")
    if current_user.role == "MANAGER":
        managed_ids = set(get_manager_subordinate_ids(db, current_user.id))
        if accountant.id not in managed_ids:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只能转给直属下属会计")

    if conversion_mode == "REUSE_CUSTOMER":
        if related_customer is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Related customer not found")
        customer = related_customer
        old_customer_name = customer.name
        customer.name = requested_name or customer.name or lead.name
        customer.contact_name = requested_contact_name or customer.contact_name or lead.contact_name
        customer.phone = requested_phone or customer.phone or lead.phone
        customer.assigned_accountant_id = assigned_accountant_id
        if customer.name != old_customer_name:
            for record in customer.billing_records:
                record.customer_name = customer.name
    else:
        default_seq = requested_code_seq or _next_customer_code_seq(db)
        existing_code_owner = db.execute(
            select(Customer.id).where(
                Customer.customer_code_seq == default_seq,
                active_filter(Customer),
                Customer.source_lead_id != lead.id,
            )
        ).scalar_one_or_none()
        if existing_code_owner is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="客户编号已被使用")
        default_suffix = requested_code_suffix or _default_customer_code_suffix(lead.source, lead.intro)
        default_code = _format_customer_code(default_seq, default_suffix)
        customer_name = requested_name or lead.name
        customer_contact_name = requested_contact_name or lead.contact_name
        customer_phone = requested_phone or lead.phone
        customer = db.execute(select(Customer).where(Customer.source_lead_id == lead.id, deleted_filter(Customer))).scalar_one_or_none()
        if customer is not None:
            restore_deleted(customer)
            customer.name = customer_name
            customer.contact_name = customer_contact_name
            customer.phone = customer_phone
            customer.assigned_accountant_id = assigned_accountant_id
            customer.source_customer_id = lead.related_customer_id
            customer.customer_code_seq = customer.customer_code_seq or default_seq
            customer.customer_code_suffix = (customer.customer_code_suffix or default_suffix).upper()
            customer.customer_code = customer.customer_code or _format_customer_code(
                customer.customer_code_seq,
                customer.customer_code_suffix,
            )
        else:
            customer = Customer(
                name=customer_name,
                contact_name=customer_contact_name,
                phone=customer_phone,
                assigned_accountant_id=assigned_accountant_id,
                customer_code_seq=default_seq,
                customer_code_suffix=default_suffix,
                customer_code=default_code,
                source_customer_id=lead.related_customer_id,
                source_lead_id=lead.id,
            )
            db.add(customer)

    lead.status = "CONVERTED"
    lead.updated_at = datetime.utcnow()

    write_operation_log(
        db,
        actor_id=current_user.id,
        action="LEAD_CONVERTED",
        entity_type="LEAD",
        entity_id=lead.id,
        detail=(
            f"customer={customer.name},accountant_id={assigned_accountant_id},"
            f"reused_customer={'Y' if conversion_mode == 'REUSE_CUSTOMER' else 'N'},"
            f"source_customer_id={lead.related_customer_id or ''},"
            f"customer_code={customer.customer_code or ''}"
        ),
    )
    db.commit()
    db.refresh(lead)
    db.refresh(customer)
    return ConvertLeadResponse(lead=lead, customer=customer)


@router.post(
    "/{lead_id}/unconvert",
    response_model=LeadOut,
    dependencies=[Depends(require_roles("OWNER", "MANAGER"))],
)
def unconvert_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    lead = _get_lead_or_404(db, lead_id)
    _ensure_lead_access(lead, current_user, db, for_write=True)
    if lead.status != "CONVERTED":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Lead is not converted")

    customer = db.execute(
        select(Customer).where(Customer.source_lead_id == lead.id, active_filter(Customer))
    ).scalar_one_or_none()
    if customer is not None:
        linked_billing = (
            db.execute(
                select(func.count(BillingRecord.id)).where(
                    BillingRecord.customer_id == customer.id,
                    active_filter(BillingRecord),
                )
            ).scalar()
            or 0
        )
        if linked_billing > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Customer has billing records, cannot revoke conversion",
            )
        mark_deleted(customer, current_user.id)

    lead.status = "FOLLOWING" if lead.last_followup_date is not None else "NEW"
    lead.updated_at = datetime.utcnow()
    write_operation_log(
        db,
        actor_id=current_user.id,
        action="LEAD_UNCONVERTED",
        entity_type="LEAD",
        entity_id=lead.id,
        detail="conversion revoked",
    )
    db.commit()
    db.refresh(lead)
    return lead
