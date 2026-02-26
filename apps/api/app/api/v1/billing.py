from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models import BillingActivity, BillingRecord, Customer, User
from app.schemas.billing import (
    BillingActivityCreate,
    BillingActivityOut,
    BillingRecordCreate,
    BillingRecordOut,
    BillingRecordUpdate,
)
from app.services.audit import write_operation_log

router = APIRouter(prefix="/billing-records", tags=["billing-records"])


def _refresh_record_amounts(record: BillingRecord) -> None:
    total = float(record.total_fee or 0)
    received = float(record.received_amount or 0)
    if received < 0:
        received = 0
    outstanding = total - received
    if outstanding < 0:
        outstanding = 0

    record.received_amount = received
    record.outstanding_amount = outstanding
    if received <= 0 and total > 0:
        record.status = "FULL_ARREARS"
    elif outstanding <= 0:
        record.status = "CLEARED"
    else:
        record.status = "PARTIAL"


@router.get("", response_model=list[BillingRecordOut])
def list_billing_records(
    keyword: Optional[str] = Query(default=None),
    payment_method: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(BillingRecord).order_by(BillingRecord.serial_no.asc(), BillingRecord.id.asc())
    if keyword:
        raw_key = keyword.strip()
        key = f"%{raw_key}%"
        conditions = [
            BillingRecord.customer_name.ilike(key),
            BillingRecord.note.ilike(key),
        ]
        if raw_key.isdigit():
            conditions.append(BillingRecord.serial_no == int(raw_key))
        stmt = stmt.where(or_(*conditions))
    if payment_method:
        stmt = stmt.where(BillingRecord.payment_method == payment_method)
    return db.execute(stmt).scalars().all()


@router.post(
    "",
    response_model=BillingRecordOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles("OWNER", "ADMIN"))],
)
def create_billing_record(
    payload: BillingRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    customer = db.execute(select(Customer).where(Customer.id == payload.customer_id)).scalar_one_or_none()
    if customer is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Customer not found")

    serial_no = payload.serial_no
    if serial_no is None:
        current_max = db.execute(select(func.max(BillingRecord.serial_no))).scalar() or 0
        serial_no = int(current_max) + 1

    record = BillingRecord(
        **payload.model_dump(exclude={"serial_no", "outstanding_amount", "customer_name"}),
        serial_no=serial_no,
        customer_name=customer.name,
    )
    if payload.outstanding_amount is not None:
        record.outstanding_amount = payload.outstanding_amount
    _refresh_record_amounts(record)
    db.add(record)
    write_operation_log(
        db,
        actor_id=current_user.id,
        action="BILLING_RECORD_CREATED",
        entity_type="BILLING",
        entity_id=serial_no,
        detail=f"customer_id={payload.customer_id},total_fee={record.total_fee}",
    )
    db.commit()
    db.refresh(record)
    return record


@router.patch(
    "/{record_id}",
    response_model=BillingRecordOut,
    dependencies=[Depends(require_roles("OWNER", "ADMIN"))],
)
def update_billing_record(
    record_id: int,
    payload: BillingRecordUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = db.execute(select(BillingRecord).where(BillingRecord.id == record_id)).scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Billing record not found")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(record, key, value)
    if payload.customer_id is not None:
        customer = db.execute(select(Customer).where(Customer.id == payload.customer_id)).scalar_one_or_none()
        if customer is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Customer not found")
        record.customer_name = customer.name
    elif payload.customer_name is not None and payload.customer_name.strip():
        # 兼容历史修正：允许仅改名称，但优先走 customer_id 绑定
        record.customer_name = payload.customer_name.strip()
    _refresh_record_amounts(record)
    write_operation_log(
        db,
        actor_id=current_user.id,
        action="BILLING_RECORD_UPDATED",
        entity_type="BILLING",
        entity_id=record.id,
        detail=f"customer_name={record.customer_name}",
    )

    db.commit()
    db.refresh(record)
    return record


@router.get("/summary")
def billing_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    total_receivable = db.execute(select(func.sum(BillingRecord.total_fee))).scalar() or 0
    total_month_fee = db.execute(select(func.sum(BillingRecord.monthly_fee))).scalar() or 0
    by_method_rows = db.execute(
        select(BillingRecord.payment_method, func.count(BillingRecord.id))
        .group_by(BillingRecord.payment_method)
        .order_by(func.count(BillingRecord.id).desc())
    ).all()
    by_status_rows = db.execute(
        select(BillingRecord.status, func.count(BillingRecord.id))
        .group_by(BillingRecord.status)
        .order_by(func.count(BillingRecord.id).desc())
    ).all()
    return {
        "total_records": db.execute(select(func.count(BillingRecord.id))).scalar() or 0,
        "total_fee": float(total_receivable),
        "total_monthly_fee": float(total_month_fee),
        "payment_method_distribution": [
            {"payment_method": row[0], "count": row[1]} for row in by_method_rows if row[0]
        ],
        "status_distribution": [{"status": row[0], "count": row[1]} for row in by_status_rows if row[0]],
    }


@router.get("/{record_id}/activities", response_model=list[BillingActivityOut])
def list_billing_activities(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = db.execute(select(BillingRecord).where(BillingRecord.id == record_id)).scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Billing record not found")

    stmt = (
        select(BillingActivity)
        .where(BillingActivity.billing_record_id == record_id)
        .order_by(BillingActivity.occurred_at.desc(), BillingActivity.id.desc())
    )
    return db.execute(stmt).scalars().all()


@router.post("/{record_id}/activities", response_model=BillingActivityOut, status_code=status.HTTP_201_CREATED)
def create_billing_activity(
    record_id: int,
    payload: BillingActivityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = db.execute(select(BillingRecord).where(BillingRecord.id == record_id)).scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Billing record not found")

    if payload.activity_type == "PAYMENT" and payload.amount <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment amount must be greater than zero")
    if payload.activity_type == "REMINDER" and payload.amount != 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reminder amount must be zero")

    activity = BillingActivity(
        billing_record_id=record.id,
        activity_type=payload.activity_type,
        occurred_at=payload.occurred_at,
        actor_id=current_user.id,
        amount=payload.amount if payload.activity_type == "PAYMENT" else 0,
        payment_nature=payload.payment_nature,
        is_prepay=payload.is_prepay,
        is_settlement=payload.is_settlement,
        content=payload.content,
        next_followup_at=payload.next_followup_at,
        note=payload.note,
    )
    db.add(activity)

    if payload.activity_type == "PAYMENT":
        record.received_amount = (record.received_amount or 0) + payload.amount
        if payload.is_settlement and record.total_fee > record.received_amount:
            record.received_amount = record.total_fee
        _refresh_record_amounts(record)

    write_operation_log(
        db,
        actor_id=current_user.id,
        action="BILLING_ACTIVITY_CREATED",
        entity_type="BILLING_ACTIVITY",
        entity_id=record.id,
        detail=f"type={payload.activity_type},amount={activity.amount}",
    )
    db.commit()
    db.refresh(activity)
    return activity
