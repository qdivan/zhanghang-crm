from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
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

router = APIRouter(prefix="/leads", tags=["leads"])


def _get_lead_or_404(db: Session, lead_id: int) -> Lead:
    lead = db.execute(select(Lead).where(Lead.id == lead_id)).scalar_one_or_none()
    if lead is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    return lead


def _ensure_lead_access(lead: Lead, current_user: User, db: Session, *, for_write: bool = False) -> None:
    if current_user.role != "ACCOUNTANT":
        return
    if lead.owner_id == current_user.id:
        return
    # 转化后的客户，允许被分配的会计继续写跟进
    if lead.customer is not None and lead.customer.assigned_accountant_id == current_user.id:
        return
    if lead.related_customer_id is not None:
        related_customer_assignee = db.execute(
            select(Customer.assigned_accountant_id).where(Customer.id == lead.related_customer_id)
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
    if current_user.role == "ACCOUNTANT":
        stmt = stmt.where(
            or_(
                Lead.owner_id == current_user.id,
                Lead.customer.has(Customer.assigned_accountant_id == current_user.id),
            )
        )

    return db.execute(stmt).scalars().all()


@router.get("/{lead_id}", response_model=LeadOut)
def get_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    lead = (
        db.execute(select(Lead).options(selectinload(Lead.customer)).where(Lead.id == lead_id))
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
    if current_user.role == "ACCOUNTANT":
        target_owner_id = current_user.id
    else:
        target_owner_id = payload.owner_id or current_user.id

    owner = db.execute(select(User).where(User.id == target_owner_id)).scalar_one_or_none()
    if owner is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Owner not found")

    related_customer_id = payload.related_customer_id
    if related_customer_id is not None:
        related_customer = db.execute(select(Customer).where(Customer.id == related_customer_id)).scalar_one_or_none()
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

    lead = Lead(
        template_type=payload.template_type,
        name=payload.name,
        grade=payload.grade,
        contact_name=payload.contact_name,
        phone=payload.phone,
        region=payload.region,
        country=payload.country,
        source=payload.source,
        contact_wechat=payload.contact_wechat,
        fax=payload.fax,
        other_contact=payload.other_contact,
        contact_start_date=payload.contact_start_date,
        service_start_text=payload.service_start_text,
        company_nature=payload.company_nature,
        service_mode=payload.service_mode,
        main_business=payload.main_business,
        intro=payload.intro,
        fee_standard=payload.fee_standard,
        first_billing_period=payload.first_billing_period,
        reserve_2=payload.reserve_2,
        reserve_3=payload.reserve_3,
        reserve_4=payload.reserve_4,
        status="NEW",
        next_reminder_at=payload.next_reminder_at,
        reminder_value=payload.reminder_value,
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
        if related_customer is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Related customer not found")
        lead.related_customer_id = related_customer.id

    lead.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(lead)
    return lead


@router.post("/{lead_id}/followups", response_model=LeadFollowupOut, status_code=status.HTTP_201_CREATED)
def create_followup(
    lead_id: int,
    payload: LeadFollowupCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    lead = _get_lead_or_404(db, lead_id)
    _ensure_lead_access(lead, current_user, db, for_write=True)

    followup = LeadFollowup(
        lead_id=lead_id,
        followup_at=payload.followup_at,
        feedback=payload.feedback,
        next_reminder_at=payload.next_reminder_at,
        notes=payload.notes,
        created_by=current_user.id,
    )
    lead.last_feedback = payload.feedback
    lead.next_reminder_at = payload.next_reminder_at
    lead.last_followup_date = payload.followup_at
    if lead.status == "NEW":
        lead.status = "FOLLOWING"
    lead.updated_at = datetime.utcnow()

    db.add(followup)
    write_operation_log(
        db,
        actor_id=current_user.id,
        action="LEAD_FOLLOWUP_CREATED",
        entity_type="LEAD",
        entity_id=lead.id,
        detail=f"followup_at={payload.followup_at}",
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
    dependencies=[Depends(require_roles("OWNER", "ADMIN"))],
)
def convert_lead(
    lead_id: int,
    payload: ConvertLeadRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    lead = _get_lead_or_404(db, lead_id)
    if lead.status == "CONVERTED":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Lead already converted")

    requested_name = (payload.customer_name or "").strip()
    requested_contact_name = (payload.customer_contact_name or "").strip()
    requested_phone = (payload.customer_phone or "").strip()

    customer: Customer
    assigned_accountant_id = payload.accountant_id
    if lead.related_customer_id is not None:
        customer = db.execute(select(Customer).where(Customer.id == lead.related_customer_id)).scalar_one_or_none()
        if customer is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Related customer not found")
        if assigned_accountant_id is None:
            assigned_accountant_id = customer.assigned_accountant_id
    else:
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

    if lead.related_customer_id is not None:
        old_customer_name = customer.name
        customer.name = requested_name or customer.name or lead.name
        customer.contact_name = requested_contact_name or customer.contact_name or lead.contact_name
        customer.phone = requested_phone or customer.phone or lead.phone
        customer.assigned_accountant_id = assigned_accountant_id
        if customer.name != old_customer_name:
            for record in customer.billing_records:
                record.customer_name = customer.name
    else:
        customer_name = requested_name or lead.name
        customer_contact_name = requested_contact_name or lead.contact_name
        customer_phone = requested_phone or lead.phone
        customer = Customer(
            name=customer_name,
            contact_name=customer_contact_name,
            phone=customer_phone,
            assigned_accountant_id=assigned_accountant_id,
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
            f"reused_customer={'Y' if lead.related_customer_id is not None else 'N'}"
        ),
    )
    db.commit()
    db.refresh(lead)
    db.refresh(customer)
    return ConvertLeadResponse(lead=lead, customer=customer)


@router.post(
    "/{lead_id}/unconvert",
    response_model=LeadOut,
    dependencies=[Depends(require_roles("OWNER", "ADMIN"))],
)
def unconvert_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    lead = _get_lead_or_404(db, lead_id)
    if lead.status != "CONVERTED":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Lead is not converted")

    customer = db.execute(select(Customer).where(Customer.source_lead_id == lead.id)).scalar_one_or_none()
    if customer is not None:
        linked_billing = (
            db.execute(select(func.count(BillingRecord.id)).where(BillingRecord.customer_id == customer.id)).scalar()
            or 0
        )
        if linked_billing > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Customer has billing records, cannot revoke conversion",
            )
        db.delete(customer)

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
