from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import Customer, Lead, LeadFollowup, User
from app.schemas.customer import CustomerDetailOut, CustomerListOut, CustomerUpdate
from app.services.audit import write_operation_log
from app.services.data_access import has_module_read_grant

router = APIRouter(prefix="/customers", tags=["customers"])


def _ensure_customer_access(
    customer: Customer,
    current_user: User,
    db: Session,
    *,
    for_write: bool = False,
) -> None:
    if current_user.role != "ACCOUNTANT":
        return
    if customer.assigned_accountant_id == current_user.id:
        return
    if not for_write and has_module_read_grant(db, current_user.id, "CUSTOMER"):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to this customer")


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
        select(Customer, User.username, Lead.template_type, Lead.grade, Lead.last_followup_date, Lead.reminder_value)
        .join(User, Customer.assigned_accountant_id == User.id)
        .join(Lead, Customer.source_lead_id == Lead.id)
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
    if current_user.role == "ACCOUNTANT" and not has_customer_read_grant:
        stmt = stmt.where(Customer.assigned_accountant_id == current_user.id)

    rows = db.execute(stmt).all()
    result: list[CustomerListOut] = []
    for customer, accountant_username, template_type, grade, last_followup_date, reminder_value in rows:
        result.append(
            CustomerListOut(
                id=customer.id,
                name=customer.name,
                contact_name=customer.contact_name,
                phone=customer.phone,
                status=customer.status,
                assigned_accountant_id=customer.assigned_accountant_id,
                accountant_username=accountant_username,
                source_lead_id=customer.source_lead_id,
                source_template_type=template_type or "",
                source_grade=grade or "",
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
    customer = (
        db.execute(select(Customer).where(Customer.id == customer_id))
        .scalar_one_or_none()
    )
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    _ensure_customer_access(customer, current_user, db)

    lead = (
        db.execute(select(Lead).options(selectinload(Lead.customer)).where(Lead.id == customer.source_lead_id))
        .scalar_one_or_none()
    )
    if lead is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source lead not found")

    followups = db.execute(
        select(LeadFollowup)
        .where(LeadFollowup.lead_id == lead.id)
        .order_by(LeadFollowup.followup_at.desc(), LeadFollowup.id.desc())
    ).scalars().all()

    accountant = db.execute(select(User).where(User.id == customer.assigned_accountant_id)).scalar_one_or_none()
    accountant_username = accountant.username if accountant else ""

    return CustomerDetailOut(
        id=customer.id,
        name=customer.name,
        contact_name=customer.contact_name,
        phone=customer.phone,
        status=customer.status,
        assigned_accountant_id=customer.assigned_accountant_id,
        accountant_username=accountant_username,
        source_lead_id=customer.source_lead_id,
        created_at=customer.created_at,
        lead=lead,
        followups=followups,
    )


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
    customer = db.execute(select(Customer).where(Customer.id == customer_id)).scalar_one_or_none()
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    _ensure_customer_access(customer, current_user, db, for_write=True)

    lead = db.execute(select(Lead).where(Lead.id == customer.source_lead_id)).scalar_one_or_none()
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
        if current_user.role == "ACCOUNTANT":
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
