from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import exists, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models import (
    BillingActivity,
    BillingAssignment,
    BillingExecutionLog,
    BillingPayment,
    BillingPaymentAllocation,
    BillingRecord,
    Customer,
    User,
)
from app.schemas.billing import (
    BillingActivityCreate,
    BillingActivityOut,
    BillingAssignmentCreate,
    BillingAssignmentOut,
    BillingAssignmentUpdate,
    BillingExecutionLogCreate,
    BillingExecutionLogOut,
    BillingPaymentAllocationOut,
    BillingPaymentCreate,
    BillingPaymentOut,
    BillingReceiptAccountEntryOut,
    BillingReceiptAccountLedgerOut,
    BillingReceiptAccountSummaryOut,
    BillingPaymentSuggestOut,
    BillingPaymentSuggestRequest,
    BillingPaymentSuggestedAllocationOut,
    BillingLedgerEntryOut,
    BillingLedgerMonthlySummaryOut,
    BillingLedgerOut,
    BillingRecordBatchCreate,
    BillingRecordCreate,
    BillingRecordOut,
    BillingRenewRequest,
    BillingTerminateRequest,
    BillingRecordUpdate,
)
from app.services.audit import write_operation_log
from app.services.data_access import has_module_read_grant
from app.services.org_scope import get_manager_subordinate_ids

router = APIRouter(prefix="/billing-records", tags=["billing-records"])


def _normalize_payment_method(value: Optional[str]) -> str:
    raw = (value or "").strip()
    if raw == "预收":
        return "预收"
    return "后收"


def _normalize_receipt_account(value: Optional[str]) -> str:
    raw = (value or "").strip()
    return raw or "未指定"


def _normalize_charge_mode(value: Optional[str]) -> str:
    return "ONE_TIME" if (value or "").strip().upper() == "ONE_TIME" else "PERIODIC"


def _normalize_amount_basis(value: Optional[str], charge_mode: str) -> str:
    token = (value or "").strip().upper()
    if charge_mode == "ONE_TIME":
        return "ONE_TIME"
    if token in {"MONTHLY", "YEARLY", "PERIOD_TOTAL"}:
        return token
    return "MONTHLY"


def _normalize_month(value: Optional[str]) -> str:
    raw = (value or "").strip()
    if len(raw) == 7 and raw[4] == "-" and raw[:4].isdigit() and raw[5:].isdigit():
        month = int(raw[5:])
        if 1 <= month <= 12:
            return raw
    return ""


def _shift_month(month_text: str, delta: int) -> str:
    normalized = _normalize_month(month_text)
    if not normalized:
        return ""
    year = int(normalized[:4])
    month = int(normalized[5:7])
    month_index = year * 12 + (month - 1) + delta
    target_year = month_index // 12
    target_month = month_index % 12 + 1
    return f"{target_year:04d}-{target_month:02d}"


def _month_end_date_text(month_text: str) -> str:
    normalized = _normalize_month(month_text)
    if not normalized:
        return ""
    year = int(normalized[:4])
    month = int(normalized[5:7])
    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)
    return (next_month - next_month.resolution).isoformat()


def _shift_date_text(date_text: str, years: int) -> str:
    raw = (date_text or "").strip()
    if not raw:
        return ""
    try:
        source = date.fromisoformat(raw)
    except ValueError:
        return raw
    try:
        target = source.replace(year=source.year + years)
    except ValueError:
        # 仅处理闰年 2/29 -> 平年 2/28
        if source.month == 2 and source.day == 29:
            target = source.replace(year=source.year + years, day=28)
        else:
            return raw
    return target.isoformat()


def _normalize_iso_date(value: Optional[str]) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""
    try:
        return date.fromisoformat(raw).isoformat()
    except ValueError:
        return ""


def _format_date(value: date) -> str:
    return value.isoformat()


def _subtract_days(value: date, days: int) -> date:
    return value.fromordinal(value.toordinal() - days)


def _add_months_clamped(value: date, months: int) -> date:
    month_index = value.year * 12 + (value.month - 1) + months
    target_year = month_index // 12
    target_month = month_index % 12 + 1
    if target_month == 12:
        next_month = date(target_year + 1, 1, 1)
    else:
        next_month = date(target_year, target_month + 1, 1)
    last_day = (next_month - next_month.resolution).day
    return date(target_year, target_month, min(value.day, last_day))


def _add_years_clamped(value: date, years: int) -> date:
    target_year = value.year + years
    try:
        return value.replace(year=target_year)
    except ValueError:
        if value.month == 2 and value.day == 29:
            return value.replace(year=target_year, day=28)
        raise


def _parse_due_month(value: Optional[str]) -> Optional[date]:
    raw = (value or "").strip()
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def _parse_service_start_date(record: BillingRecord) -> Optional[date]:
    collection_start = _parse_due_month(record.collection_start_date)
    if collection_start is not None:
        return collection_start
    normalized_month = _normalize_month(record.period_start_month)
    if not normalized_month:
        return None
    return date.fromisoformat(f"{normalized_month}-01")


def _normalize_charge_category(value: Optional[str]) -> str:
    raw = (value or "").strip()
    return raw or "代账"


def _build_receivable_summary(record: BillingRecord) -> str:
    category = (record.charge_category or "").strip() or "代账"
    if record.charge_mode == "ONE_TIME":
        return (record.summary or "").strip() or f"{category}一次性项目"
    period_text = (record.receivable_period_text or "").strip()
    if (record.summary or "").strip():
        return (record.summary or "").strip()
    if period_text and period_text != "-":
        return f"{category} {period_text}"
    return f"{category}服务费"


def _build_payment_summary(record: BillingRecord, content: str, payment_ref: str = "") -> str:
    summary = (content or "").strip()
    if summary:
        return summary
    base = _build_receivable_summary(record)
    if payment_ref:
        return f"收款入账 {payment_ref} · {base}"
    return f"收款入账 · {base}"


def _apply_billing_business_defaults(record: BillingRecord) -> None:
    record.charge_mode = _normalize_charge_mode(record.charge_mode)
    record.charge_category = _normalize_charge_category(record.charge_category)
    record.amount_basis = _normalize_amount_basis(record.amount_basis, record.charge_mode)
    record.collection_start_date = _normalize_iso_date(record.collection_start_date)
    record.due_month = _normalize_iso_date(record.due_month)
    record.period_start_month = _normalize_month(record.period_start_month)
    record.period_end_month = _normalize_month(record.period_end_month)
    record.payment_method = _normalize_payment_method(record.payment_method)
    if record.charge_mode == "ONE_TIME":
        record.period_start_month = ""
        record.period_end_month = ""
        if not record.collection_start_date:
            record.collection_start_date = record.due_month or date.today().isoformat()
        if not record.due_month:
            record.due_month = record.collection_start_date or date.today().isoformat()
        return

    if not record.collection_start_date and record.period_start_month:
        record.collection_start_date = f"{record.period_start_month}-01"
    if record.period_start_month and not record.period_end_month and not record.due_month:
        record.period_end_month = _shift_month(record.period_start_month, 11)
        record.due_month = _month_end_date_text(record.period_end_month)
    if record.collection_start_date and not record.due_month:
        service_start = date.fromisoformat(record.collection_start_date)
        if record.amount_basis == "MONTHLY":
            record.due_month = _format_date(_subtract_days(_add_months_clamped(service_start, 1), 1))
        else:
            record.due_month = _format_date(_subtract_days(_add_years_clamped(service_start, 1), 1))
    if not record.collection_start_date and record.due_month:
        record.collection_start_date = f"{record.due_month[:7]}-01"
    if not record.period_start_month and record.collection_start_date:
        record.period_start_month = record.collection_start_date[:7]
    if not record.period_end_month and record.due_month:
        record.period_end_month = record.due_month[:7]


def _ensure_valid_record_dates(record: BillingRecord) -> None:
    service_start = _parse_due_month(record.collection_start_date)
    due_date = _parse_due_month(record.due_month)
    if service_start is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请填写服务开始日期")
    if due_date is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请填写到期日期")
    if due_date < service_start:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="到期日期不能早于服务开始日期")


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


def _apply_accountant_scope(stmt, db: Session, current_user: User, has_billing_read_grant: bool):
    if current_user.role == "MANAGER":
        managed_ids = get_manager_subordinate_ids(db, current_user.id)
        return stmt.where(BillingRecord.customer.has(Customer.assigned_accountant_id.in_(managed_ids)))
    if current_user.role != "ACCOUNTANT" or has_billing_read_grant:
        return stmt
    assignment_visible_expr = exists(
        select(BillingAssignment.id).where(
            BillingAssignment.billing_record_id == BillingRecord.id,
            BillingAssignment.assignee_user_id == current_user.id,
            BillingAssignment.is_active.is_(True),
        )
    )
    return stmt.where(
        or_(
            BillingRecord.customer.has(Customer.assigned_accountant_id == current_user.id),
            assignment_visible_expr,
        )
    )


def _matches_receipt_account(receipt_account: str, target_account: str) -> bool:
    normalized_target = _normalize_receipt_account(target_account)
    normalized_value = _normalize_receipt_account(receipt_account)
    return normalized_value == normalized_target


def _ensure_receipt_account_ledger_access(db: Session, current_user: User) -> None:
    if current_user.role in {"OWNER", "ADMIN", "MANAGER"}:
        return
    if current_user.role == "ACCOUNTANT" and has_module_read_grant(db, current_user.id, "BILLING"):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to receipt account ledger")


def _record_matches_billing_month(record: BillingRecord, billing_month: Optional[str]) -> bool:
    normalized_month = _normalize_month(billing_month)
    if not normalized_month:
        return True

    if record.charge_mode == "ONE_TIME":
        service_month = (record.collection_start_date or "").strip()[:7]
        due_month = (record.due_month or "").strip()[:7]
        return service_month == normalized_month or due_month == normalized_month

    start_month = _normalize_month(record.period_start_month)
    end_month = _normalize_month(record.period_end_month)
    if not start_month and record.collection_start_date:
        start_month = _normalize_month((record.collection_start_date or "")[:7])
    if not end_month and record.due_month:
        end_month = _normalize_month((record.due_month or "")[:7])
    if end_month and not start_month:
        start_month = _shift_month(end_month, -11)
    if start_month and not end_month:
        end_month = _shift_month(start_month, 11)

    if start_month and end_month:
        return start_month <= normalized_month <= end_month
    if start_month:
        return start_month == normalized_month
    if end_month:
        return end_month == normalized_month
    return False


def _record_matches_filters(
    record: BillingRecord,
    keyword: Optional[str] = None,
    customer_id: Optional[int] = None,
    receipt_account: Optional[str] = None,
    billing_month: Optional[str] = None,
    contact_name: Optional[str] = None,
    payment_method: Optional[str] = None,
    status_value: Optional[str] = None,
) -> bool:
    raw_keyword = (keyword or "").strip()
    if raw_keyword:
        keyword_lower = raw_keyword.lower()
        haystacks = [
            (record.customer_name or "").lower(),
            (record.note or "").lower(),
            (record.summary or "").lower(),
            ((record.customer.contact_name if record.customer else "") or "").lower(),
        ]
        matched = any(keyword_lower in item for item in haystacks)
        if not matched and raw_keyword.isdigit():
            matched = record.serial_no == int(raw_keyword)
        if not matched:
            return False

    if customer_id and record.customer_id != customer_id:
        return False

    if contact_name:
        contact_key = contact_name.strip().lower()
        if contact_key:
            current_contact = ((record.customer.contact_name if record.customer else "") or "").lower()
            if contact_key not in current_contact:
                return False

    if payment_method:
        normalized_payment_method = _normalize_payment_method(payment_method)
        if _normalize_payment_method(record.payment_method) != normalized_payment_method:
            return False

    if status_value and record.status != status_value:
        return False

    if not _record_matches_billing_month(record, billing_month):
        return False

    if receipt_account:
        if not any(
            item.activity_type == "PAYMENT"
            and float(item.amount or 0) > 0
            and _matches_receipt_account(item.receipt_account or "", receipt_account)
            for item in record.activities
        ):
            return False

    return True
    return stmt.where(
        or_(
            BillingRecord.customer.has(Customer.assigned_accountant_id == current_user.id),
            assignment_visible_expr,
        )
    )


def _has_active_assignment(db: Session, record_id: int, user_id: int) -> bool:
    assignment_match = db.execute(
        select(BillingAssignment.id).where(
            BillingAssignment.billing_record_id == record_id,
            BillingAssignment.assignee_user_id == user_id,
            BillingAssignment.is_active.is_(True),
        )
    ).scalar_one_or_none()
    return assignment_match is not None


def _ensure_billing_access(record: BillingRecord, db: Session, current_user: User, *, for_write: bool = False) -> None:
    if current_user.role not in {"ACCOUNTANT", "MANAGER"}:
        return
    if record.customer_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to this billing record")

    if current_user.role == "MANAGER":
        managed_ids = set(get_manager_subordinate_ids(db, current_user.id))
        if record.customer is not None and record.customer.assigned_accountant_id in managed_ids:
            return
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to this billing record")

    own_customer = db.execute(
        select(Customer.id).where(
            Customer.id == record.customer_id,
            Customer.assigned_accountant_id == current_user.id,
        )
    ).scalar_one_or_none()
    if own_customer is not None:
        return
    if _has_active_assignment(db, record.id, current_user.id) and not for_write:
        return
    if not for_write and has_module_read_grant(db, current_user.id, "BILLING"):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to this billing record")


def _ensure_execution_log_write_access(record: BillingRecord, db: Session, current_user: User) -> None:
    if current_user.role not in {"ACCOUNTANT", "MANAGER"}:
        return
    if current_user.role == "MANAGER":
        managed_ids = set(get_manager_subordinate_ids(db, current_user.id))
        own_customer = db.execute(
            select(Customer.id).where(
                Customer.id == record.customer_id,
                Customer.assigned_accountant_id.in_(managed_ids),
            )
        ).scalar_one_or_none()
        if own_customer is not None:
            return
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No write access to execution logs")
    own_customer = db.execute(
        select(Customer.id).where(
            Customer.id == record.customer_id,
            Customer.assigned_accountant_id == current_user.id,
        )
    ).scalar_one_or_none()
    if own_customer is not None:
        return
    if _has_active_assignment(db, record.id, current_user.id):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No write access to execution logs")


def _get_record_or_404(db: Session, record_id: int) -> BillingRecord:
    record = db.execute(select(BillingRecord).where(BillingRecord.id == record_id)).scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Billing record not found")
    return record


def _build_billing_record(
    payload: BillingRecordCreate,
    customer: Customer,
    serial_no: int,
) -> BillingRecord:
    record = BillingRecord(
        **payload.model_dump(exclude={"serial_no", "outstanding_amount", "customer_name", "payment_method"}),
        serial_no=serial_no,
        customer_name=customer.name,
        payment_method=_normalize_payment_method(payload.payment_method),
    )
    _apply_billing_business_defaults(record)
    _ensure_valid_record_dates(record)
    if payload.outstanding_amount is not None:
        record.outstanding_amount = payload.outstanding_amount
    _refresh_record_amounts(record)
    return record


def _ensure_customer_billing_write_access(customer: Customer, db: Session, current_user: User) -> None:
    if current_user.role == "MANAGER":
        managed_ids = set(get_manager_subordinate_ids(db, current_user.id))
        if customer.assigned_accountant_id in managed_ids:
            return
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No write access to this customer billing")
    if current_user.role != "ACCOUNTANT":
        return
    if customer.assigned_accountant_id == current_user.id:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No write access to this customer billing")


def _ensure_customer_billing_read_access(customer: Customer, db: Session, current_user: User) -> None:
    if current_user.role == "MANAGER":
        managed_ids = set(get_manager_subordinate_ids(db, current_user.id))
        if customer.assigned_accountant_id in managed_ids:
            return
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No read access to this customer billing")
    if current_user.role != "ACCOUNTANT":
        return
    if customer.assigned_accountant_id == current_user.id:
        return
    if has_module_read_grant(db, current_user.id, "BILLING"):
        return
    assignment_match = db.execute(
        select(BillingAssignment.id)
        .join(BillingRecord, BillingAssignment.billing_record_id == BillingRecord.id)
        .where(
            BillingRecord.customer_id == customer.id,
            BillingAssignment.assignee_user_id == current_user.id,
            BillingAssignment.is_active.is_(True),
        )
        .limit(1)
    ).scalar_one_or_none()
    if assignment_match is not None:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No read access to this customer billing")


def _outstanding_records_by_strategy(
    db: Session,
    customer_id: int,
    strategy: str,
) -> list[BillingRecord]:
    records = db.execute(
        select(BillingRecord)
        .where(BillingRecord.customer_id == customer_id)
        .order_by(BillingRecord.id.asc())
    ).scalars().all()
    outstanding_records = [item for item in records if float(item.outstanding_amount or 0) > 0]
    if strategy == "SERIAL_ASC":
        outstanding_records.sort(key=lambda item: (item.serial_no, item.id))
    elif strategy == "AMOUNT_DESC":
        outstanding_records.sort(key=lambda item: (-float(item.outstanding_amount or 0), item.id))
    else:
        outstanding_records.sort(
            key=lambda item: (
                (item.due_month or "9999-99-99") if (item.due_month or "").strip() else "9999-99-99",
                item.serial_no,
                item.id,
            )
        )
    return outstanding_records


@router.get("", response_model=list[BillingRecordOut])
def list_billing_records(
    keyword: Optional[str] = Query(default=None),
    customer_id: Optional[int] = Query(default=None),
    receipt_account: Optional[str] = Query(default=None),
    contact_name: Optional[str] = Query(default=None),
    payment_method: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    has_billing_read_grant = False
    if current_user.role == "ACCOUNTANT":
        has_billing_read_grant = has_module_read_grant(db, current_user.id, "BILLING")

    stmt = select(BillingRecord).options(selectinload(BillingRecord.activities))
    stmt = _apply_accountant_scope(stmt, db, current_user, has_billing_read_grant)
    stmt = stmt.order_by(BillingRecord.serial_no.asc(), BillingRecord.id.asc())
    if keyword:
        raw_key = keyword.strip()
        key = f"%{raw_key}%"
        conditions = [
            BillingRecord.customer_name.ilike(key),
            BillingRecord.note.ilike(key),
            BillingRecord.summary.ilike(key),
            BillingRecord.customer.has(Customer.contact_name.ilike(key)),
        ]
        if raw_key.isdigit():
            conditions.append(BillingRecord.serial_no == int(raw_key))
        stmt = stmt.where(or_(*conditions))
    if customer_id:
        stmt = stmt.where(BillingRecord.customer_id == customer_id)
    if receipt_account:
        normalized_account = _normalize_receipt_account(receipt_account)
        account_conditions = [
            BillingActivity.billing_record_id == BillingRecord.id,
            BillingActivity.activity_type == "PAYMENT",
            BillingActivity.amount > 0,
        ]
        if normalized_account == "未指定":
            account_conditions.append(
                or_(
                    BillingActivity.receipt_account == "",
                    BillingActivity.receipt_account == "未指定",
                    BillingActivity.receipt_account.is_(None),
                )
            )
        else:
            account_conditions.append(BillingActivity.receipt_account == normalized_account)
        stmt = stmt.where(exists(select(BillingActivity.id).where(*account_conditions)))
    if contact_name:
        contact_key = contact_name.strip()
        if contact_key:
            stmt = stmt.where(BillingRecord.customer.has(Customer.contact_name.ilike(f"%{contact_key}%")))
    if payment_method:
        stmt = stmt.where(BillingRecord.payment_method == payment_method)
    return db.execute(stmt).scalars().all()


@router.post(
    "",
    response_model=BillingRecordOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles("OWNER", "ADMIN", "MANAGER"))],
)
def create_billing_record(
    payload: BillingRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    customer = db.execute(select(Customer).where(Customer.id == payload.customer_id)).scalar_one_or_none()
    if customer is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Customer not found")
    _ensure_customer_billing_write_access(customer, db, current_user)

    serial_no = payload.serial_no
    if serial_no is None:
        current_max = db.execute(select(func.max(BillingRecord.serial_no))).scalar() or 0
        serial_no = int(current_max) + 1

    record = _build_billing_record(payload, customer, serial_no)
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


@router.post(
    "/batch",
    response_model=list[BillingRecordOut],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles("OWNER", "ADMIN", "MANAGER"))],
)
def create_billing_records_batch(
    payload: BillingRecordBatchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    next_serial_no = int(db.execute(select(func.max(BillingRecord.serial_no))).scalar() or 0)
    created_records: list[BillingRecord] = []

    for item in payload.records:
        customer = db.execute(select(Customer).where(Customer.id == item.customer_id)).scalar_one_or_none()
        if customer is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Customer not found")
        _ensure_customer_billing_write_access(customer, db, current_user)

        serial_no = item.serial_no
        if serial_no is None:
            next_serial_no += 1
            serial_no = next_serial_no
        else:
            next_serial_no = max(next_serial_no, int(serial_no))

        record = _build_billing_record(item, customer, serial_no)
        db.add(record)
        created_records.append(record)
        write_operation_log(
            db,
            actor_id=current_user.id,
            action="BILLING_RECORD_CREATED",
            entity_type="BILLING",
            entity_id=serial_no,
            detail=f"customer_id={item.customer_id},total_fee={record.total_fee},batch=Y",
        )

    db.commit()
    for record in created_records:
        db.refresh(record)
    return created_records


@router.patch(
    "/{record_id}",
    response_model=BillingRecordOut,
    dependencies=[Depends(require_roles("OWNER", "ADMIN", "MANAGER"))],
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
    _ensure_billing_access(record, db, current_user, for_write=True)

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(record, key, value)
    _apply_billing_business_defaults(record)
    _ensure_valid_record_dates(record)
    if payload.customer_id is not None:
        customer = db.execute(select(Customer).where(Customer.id == payload.customer_id)).scalar_one_or_none()
        if customer is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Customer not found")
        _ensure_customer_billing_write_access(customer, db, current_user)
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


@router.post(
    "/{record_id}/renew",
    response_model=BillingRecordOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles("OWNER", "ADMIN", "MANAGER"))],
)
def renew_billing_record(
    record_id: int,
    payload: BillingRenewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = _get_record_or_404(db, record_id)
    _ensure_billing_access(record, db, current_user, for_write=True)
    serial_no = int(db.execute(select(func.max(BillingRecord.serial_no))).scalar() or 0) + 1
    provided_fields = set(payload.model_fields_set)
    legacy_note_only = provided_fields.issubset({"note"}) and payload.note is not None

    renewed = BillingRecord(
        serial_no=serial_no,
        customer_id=record.customer_id,
        customer_name=record.customer_name,
        charge_category=payload.charge_category if payload.charge_category is not None else record.charge_category,
        charge_mode=payload.charge_mode if payload.charge_mode is not None else record.charge_mode,
        amount_basis=payload.amount_basis if payload.amount_basis is not None else record.amount_basis,
        summary=payload.summary if payload.summary is not None else f"{(record.summary or '').strip()}（续费）",
        total_fee=float(payload.total_fee) if payload.total_fee is not None else float(record.total_fee or 0),
        monthly_fee=float(payload.monthly_fee) if payload.monthly_fee is not None else float(record.monthly_fee or 0),
        billing_cycle_text=payload.billing_cycle_text if payload.billing_cycle_text is not None else record.billing_cycle_text,
        period_start_month=(
            payload.period_start_month
            if payload.period_start_month is not None
            else (_shift_month(record.period_start_month, 12) if record.period_start_month else "")
        ),
        period_end_month=(
            payload.period_end_month
            if payload.period_end_month is not None
            else (_shift_month(record.period_end_month, 12) if record.period_end_month else "")
        ),
        collection_start_date=(
            payload.collection_start_date
            if payload.collection_start_date is not None
            else (_shift_date_text(record.collection_start_date, 1) if record.collection_start_date else "")
        ),
        due_month=(
            payload.due_month
            if payload.due_month is not None
            else (_shift_date_text(record.due_month, 1) if record.due_month else "")
        ),
        payment_method=payload.payment_method if payload.payment_method is not None else record.payment_method,
        status=payload.status if payload.status is not None else "FULL_ARREARS",
        received_amount=float(payload.received_amount) if payload.received_amount is not None else 0,
        outstanding_amount=float(record.total_fee or 0),
        note=(
            f"{(record.note or '').strip()} 续费自#{record.serial_no}".strip()
            if legacy_note_only or payload.note is None
            else payload.note
        ),
        extra_note=(
            (payload.note or "").strip()
            if legacy_note_only
            else (payload.extra_note if payload.extra_note is not None else record.extra_note)
        ),
        color_tag=payload.color_tag if payload.color_tag is not None else record.color_tag,
    )
    _apply_billing_business_defaults(renewed)
    _ensure_valid_record_dates(renewed)
    _refresh_record_amounts(renewed)
    db.add(renewed)

    write_operation_log(
        db,
        actor_id=current_user.id,
        action="BILLING_RECORD_RENEWED",
        entity_type="BILLING",
        entity_id=renewed.serial_no,
        detail=f"source_record_id={record.id},source_serial_no={record.serial_no}",
    )
    db.commit()
    db.refresh(renewed)
    return renewed


@router.post(
    "/{record_id}/terminate",
    response_model=BillingRecordOut,
    dependencies=[Depends(require_roles("OWNER", "ADMIN", "MANAGER"))],
)
def terminate_billing_record(
    record_id: int,
    payload: BillingTerminateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = _get_record_or_404(db, record_id)
    _ensure_billing_access(record, db, current_user, for_write=True)
    terminated_at = payload.terminated_at
    service_start = _parse_service_start_date(record)
    if service_start is not None and terminated_at < service_start:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="终止日期不能早于服务开始日期",
        )
    current_due_date = _parse_due_month(record.due_month)
    if current_due_date is not None and terminated_at > current_due_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="终止日期不能晚于当前到期日",
        )

    reduced_fee = float(payload.reduced_fee or 0)
    new_total = max(float(record.total_fee or 0) - reduced_fee, 0.0)

    record.total_fee = new_total
    record.due_month = terminated_at.isoformat()
    if record.charge_mode == "PERIODIC":
        record.period_end_month = terminated_at.isoformat()[:7]
    reason_text = payload.reason.strip() or "提前终止合同"
    append_note = f"[{terminated_at.isoformat()}]{reason_text}, 冲减费用:{reduced_fee:.2f}"
    record.note = f"{(record.note or '').strip()} {append_note}".strip()
    _refresh_record_amounts(record)

    write_operation_log(
        db,
        actor_id=current_user.id,
        action="BILLING_RECORD_TERMINATED",
        entity_type="BILLING",
        entity_id=record.id,
        detail=f"terminated_at={terminated_at},reduced_fee={reduced_fee}",
    )
    db.commit()
    db.refresh(record)
    return record


@router.post("/payments/suggest", response_model=BillingPaymentSuggestOut)
def suggest_billing_payment_allocations(
    payload: BillingPaymentSuggestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    customer = db.execute(select(Customer).where(Customer.id == payload.customer_id)).scalar_one_or_none()
    if customer is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Customer not found")
    _ensure_customer_billing_write_access(customer, db, current_user)

    records = _outstanding_records_by_strategy(db, customer.id, payload.strategy)
    remaining = float(payload.amount)
    allocations: list[BillingPaymentSuggestedAllocationOut] = []
    outstanding_total = float(sum(float(item.outstanding_amount or 0) for item in records))
    suggested_total = 0.0
    for record in records:
        record_outstanding = float(record.outstanding_amount or 0)
        suggested = min(record_outstanding, remaining) if remaining > 0 else 0.0
        allocations.append(
            BillingPaymentSuggestedAllocationOut(
                billing_record_id=record.id,
                serial_no=record.serial_no,
                summary=record.summary or record.note or "",
                due_month=record.due_month or "",
                outstanding_amount=record_outstanding,
                suggested_amount=float(suggested),
            )
        )
        suggested_total += float(suggested)
        remaining -= float(suggested)
    return BillingPaymentSuggestOut(
        customer_id=customer.id,
        amount=float(payload.amount),
        strategy=payload.strategy,
        outstanding_total=float(outstanding_total),
        suggested_total=float(suggested_total),
        remaining_amount=float(max(remaining, 0.0)),
        allocations=allocations,
    )


@router.post("/payments", response_model=BillingPaymentOut, status_code=status.HTTP_201_CREATED)
def create_billing_payment(
    payload: BillingPaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    customer = db.execute(select(Customer).where(Customer.id == payload.customer_id)).scalar_one_or_none()
    if customer is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Customer not found")
    _ensure_customer_billing_write_access(customer, db, current_user)

    allocation_map: dict[int, float] = {}
    for item in payload.allocations:
        current = allocation_map.get(item.billing_record_id, 0.0)
        allocation_map[item.billing_record_id] = float(current) + float(item.allocated_amount)
    if not allocation_map:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No allocations provided")

    allocated_total = float(sum(allocation_map.values()))
    if abs(allocated_total - float(payload.amount)) > 0.01:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Allocated total must equal payment amount")

    target_records = db.execute(
        select(BillingRecord).where(
            BillingRecord.customer_id == customer.id,
            BillingRecord.id.in_(list(allocation_map.keys())),
        )
    ).scalars().all()
    if len(target_records) != len(allocation_map):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid billing records in allocations")
    target_record_map = {item.id: item for item in target_records}

    for record in target_records:
        _ensure_billing_access(record, db, current_user, for_write=True)

    payment = BillingPayment(
        customer_id=customer.id,
        occurred_at=payload.occurred_at,
        amount=float(payload.amount),
        strategy=payload.strategy,
        receipt_account=_normalize_receipt_account(payload.receipt_account),
        note=(payload.note or "").strip(),
        created_by_user_id=current_user.id,
    )
    db.add(payment)
    db.flush()

    for record_id, allocation_amount in allocation_map.items():
        record = target_record_map[record_id]
        amount_value = float(allocation_amount)
        allocation = BillingPaymentAllocation(
            payment_id=payment.id,
            billing_record_id=record.id,
            allocated_amount=amount_value,
        )
        db.add(allocation)

        record.received_amount = float(record.received_amount or 0) + amount_value
        _refresh_record_amounts(record)

        db.add(
            BillingActivity(
                billing_record_id=record.id,
                payment_id=payment.id,
                activity_type="PAYMENT",
                occurred_at=payload.occurred_at,
                actor_id=current_user.id,
                amount=amount_value,
                payment_nature="ONE_OFF",
                receipt_account=payment.receipt_account,
                is_prepay=False,
                is_settlement=False,
                content=f"客户统一收款分摊（支付单#{payment.id}）",
                note=(payload.note or "").strip(),
            )
        )

    write_operation_log(
        db,
        actor_id=current_user.id,
        action="BILLING_PAYMENT_CREATED",
        entity_type="BILLING_PAYMENT",
        entity_id=payment.id,
        detail=(
            f"customer_id={customer.id},amount={payment.amount},"
            f"allocations={len(allocation_map)},receipt_account={payment.receipt_account}"
        ),
    )
    db.commit()
    db.refresh(payment)
    payment_allocations = db.execute(
        select(BillingPaymentAllocation).where(BillingPaymentAllocation.payment_id == payment.id)
    ).scalars().all()

    return BillingPaymentOut(
        id=payment.id,
        customer_id=payment.customer_id,
        occurred_at=payment.occurred_at,
        amount=float(payment.amount),
        strategy=payment.strategy,
        receipt_account=payment.receipt_account,
        note=payment.note,
        created_by_user_id=payment.created_by_user_id,
        created_at=payment.created_at,
        allocations=[
            BillingPaymentAllocationOut(
                id=item.id,
                billing_record_id=item.billing_record_id,
                allocated_amount=float(item.allocated_amount),
            )
            for item in payment_allocations
        ],
    )


@router.get("/ledger", response_model=BillingLedgerOut)
def get_customer_billing_ledger(
    customer_id: int = Query(..., gt=0),
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    customer = db.execute(select(Customer).where(Customer.id == customer_id)).scalar_one_or_none()
    if customer is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Customer not found")
    _ensure_customer_billing_read_access(customer, db, current_user)

    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="date_from must be <= date_to")

    def _in_range(target: date) -> bool:
        if date_from and target < date_from:
            return False
        if date_to and target > date_to:
            return False
        return True

    records = db.execute(
        select(BillingRecord).where(BillingRecord.customer_id == customer.id).order_by(BillingRecord.id.asc())
    ).scalars().all()
    record_map = {item.id: item for item in records}

    raw_entries: list[tuple[date, int, int, BillingLedgerEntryOut]] = []
    receivable_total = 0.0
    received_total = 0.0

    for record in records:
        receivable_date = _parse_due_month(record.due_month) or record.created_at.date()
        receivable_amount = float(record.total_fee or 0)
        if receivable_amount > 0 and _in_range(receivable_date):
            raw_entries.append(
                (
                    receivable_date,
                    0,
                    record.id,
                    BillingLedgerEntryOut(
                        occurred_at=receivable_date,
                        summary=_build_receivable_summary(record),
                        receivable_amount=receivable_amount,
                        received_amount=0.0,
                        balance=0.0,
                        source_type="RECEIVABLE",
                        billing_record_id=record.id,
                        receipt_account="",
                    ),
                )
            )

    payment_rows = db.execute(
        select(BillingPayment)
        .where(BillingPayment.customer_id == customer.id)
        .order_by(BillingPayment.occurred_at.asc(), BillingPayment.id.asc())
    ).scalars().all()
    for payment in payment_rows:
        if not _in_range(payment.occurred_at):
            continue
        receipt_account = _normalize_receipt_account(payment.receipt_account)
        raw_entries.append(
            (
                payment.occurred_at,
                1,
                payment.id,
                BillingLedgerEntryOut(
                    occurred_at=payment.occurred_at,
                    summary=(payment.note or "").strip() or f"统一收款入账（{receipt_account}）",
                    receivable_amount=0.0,
                    received_amount=float(payment.amount or 0),
                    balance=0.0,
                    source_type="PAYMENT",
                    billing_record_id=None,
                    receipt_account=receipt_account,
                ),
            )
        )

    direct_payment_rows = db.execute(
        select(BillingActivity)
        .options(selectinload(BillingActivity.billing_record))
        .join(BillingRecord, BillingActivity.billing_record_id == BillingRecord.id)
        .where(
            BillingRecord.customer_id == customer.id,
            BillingActivity.activity_type == "PAYMENT",
            BillingActivity.amount > 0,
            BillingActivity.payment_id.is_(None),
        )
        .order_by(BillingActivity.occurred_at.asc(), BillingActivity.id.asc())
    ).scalars().all()
    for activity in direct_payment_rows:
        if not _in_range(activity.occurred_at):
            continue
        record = record_map.get(activity.billing_record_id) or activity.billing_record
        if record is None:
            continue
        receipt_account = _normalize_receipt_account(activity.receipt_account)
        raw_entries.append(
            (
                activity.occurred_at,
                2,
                activity.id,
                BillingLedgerEntryOut(
                    occurred_at=activity.occurred_at,
                    summary=_build_payment_summary(record, activity.content, receipt_account),
                    receivable_amount=0.0,
                    received_amount=float(activity.amount or 0),
                    balance=0.0,
                    source_type="PAYMENT",
                    billing_record_id=record.id,
                    receipt_account=receipt_account,
                ),
            )
        )

    raw_entries.sort(key=lambda item: (item[0], item[1], item[2]))

    balance = 0.0
    entries: list[BillingLedgerEntryOut] = []
    for _, _, _, item in raw_entries:
        receivable_total += float(item.receivable_amount or 0)
        received_total += float(item.received_amount or 0)
        balance += float(item.receivable_amount or 0) - float(item.received_amount or 0)
        entries.append(
            BillingLedgerEntryOut(
                occurred_at=item.occurred_at,
                summary=item.summary,
                receivable_amount=float(item.receivable_amount),
                received_amount=float(item.received_amount),
                balance=float(balance),
                source_type=item.source_type,
                billing_record_id=item.billing_record_id,
                receipt_account=item.receipt_account,
            )
        )

    monthly_buckets: dict[str, dict[str, float]] = {}
    for item in entries:
        month_key = item.occurred_at.strftime("%Y-%m")
        bucket = monthly_buckets.setdefault(
            month_key,
            {
                "receivable_total": 0.0,
                "received_total": 0.0,
                "ending_balance": 0.0,
            },
        )
        bucket["receivable_total"] += float(item.receivable_amount or 0)
        bucket["received_total"] += float(item.received_amount or 0)
        bucket["ending_balance"] = float(item.balance or 0)

    monthly_summaries = [
        BillingLedgerMonthlySummaryOut(
            month=month_key,
            receivable_total=float(values["receivable_total"]),
            received_total=float(values["received_total"]),
            net_change=float(values["receivable_total"] - values["received_total"]),
            ending_balance=float(values["ending_balance"]),
        )
        for month_key, values in sorted(monthly_buckets.items(), key=lambda item: item[0])
    ]

    return BillingLedgerOut(
        customer_id=customer.id,
        customer_name=customer.name,
        date_from=date_from,
        date_to=date_to,
        receivable_total=float(receivable_total),
        received_total=float(received_total),
        balance=float(balance),
        monthly_summaries=monthly_summaries,
        entries=entries,
    )


@router.get(
    "/receipt-account-ledger",
    response_model=BillingReceiptAccountLedgerOut,
)
def get_receipt_account_ledger(
    receipt_account: Optional[str] = Query(default=None),
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="date_from must be <= date_to")
    _ensure_receipt_account_ledger_access(db, current_user)
    managed_ids = set(get_manager_subordinate_ids(db, current_user.id)) if current_user.role == "MANAGER" else set()

    normalized_account = (receipt_account or "").strip()

    def _in_range(target: date) -> bool:
        if date_from and target < date_from:
            return False
        if date_to and target > date_to:
            return False
        return True

    raw_events: list[tuple[date, int, int, BillingReceiptAccountEntryOut]] = []

    payment_rows = db.execute(
        select(BillingPayment, Customer, User.username)
        .join(Customer, BillingPayment.customer_id == Customer.id)
        .outerjoin(User, BillingPayment.created_by_user_id == User.id)
        .order_by(BillingPayment.occurred_at.asc(), BillingPayment.id.asc())
    ).all()
    for payment, customer, username in payment_rows:
        if current_user.role == "MANAGER" and customer.assigned_accountant_id not in managed_ids:
            continue
        account_name = _normalize_receipt_account(payment.receipt_account)
        if normalized_account and account_name != normalized_account:
            continue
        if not _in_range(payment.occurred_at):
            continue
        raw_events.append(
            (
                payment.occurred_at,
                0,
                payment.id,
                BillingReceiptAccountEntryOut(
                    occurred_at=payment.occurred_at,
                    receipt_account=account_name,
                    customer_name=customer.name,
                    summary=(payment.note or "").strip() or "统一收款入账",
                    received_amount=float(payment.amount or 0),
                    cumulative_received=0.0,
                    actor_username=username or "",
                    payment_id=payment.id,
                    billing_record_id=None,
                ),
            )
        )

    direct_payment_rows = db.execute(
        select(BillingActivity, BillingRecord, Customer, User.username)
        .join(BillingRecord, BillingActivity.billing_record_id == BillingRecord.id)
        .join(Customer, BillingRecord.customer_id == Customer.id)
        .outerjoin(User, BillingActivity.actor_id == User.id)
        .where(
            BillingActivity.activity_type == "PAYMENT",
            BillingActivity.amount > 0,
            BillingActivity.payment_id.is_(None),
        )
        .order_by(BillingActivity.occurred_at.asc(), BillingActivity.id.asc())
    ).all()
    for activity, record, customer, username in direct_payment_rows:
        if current_user.role == "MANAGER" and customer.assigned_accountant_id not in managed_ids:
            continue
        account_name = _normalize_receipt_account(activity.receipt_account)
        if normalized_account and account_name != normalized_account:
            continue
        if not _in_range(activity.occurred_at):
            continue
        raw_events.append(
            (
                activity.occurred_at,
                1,
                activity.id,
                BillingReceiptAccountEntryOut(
                    occurred_at=activity.occurred_at,
                    receipt_account=account_name,
                    customer_name=customer.name,
                    summary=_build_payment_summary(record, activity.content, account_name),
                    received_amount=float(activity.amount or 0),
                    cumulative_received=0.0,
                    actor_username=username or "",
                    payment_id=None,
                    billing_record_id=record.id,
                ),
            )
        )

    raw_events.sort(key=lambda item: (item[0], item[1], item[2]))

    cumulative = 0.0
    entries: list[BillingReceiptAccountEntryOut] = []
    account_buckets: dict[str, dict[str, object]] = {}
    for _, _, _, item in raw_events:
        cumulative += float(item.received_amount or 0)
        entries.append(
            BillingReceiptAccountEntryOut(
                occurred_at=item.occurred_at,
                receipt_account=item.receipt_account,
                customer_name=item.customer_name,
                summary=item.summary,
                received_amount=float(item.received_amount),
                cumulative_received=float(cumulative),
                actor_username=item.actor_username,
                payment_id=item.payment_id,
                billing_record_id=item.billing_record_id,
            )
        )
        bucket = account_buckets.setdefault(
            item.receipt_account,
            {"payment_count": 0, "total_received": 0.0, "last_received_at": None},
        )
        bucket["payment_count"] = int(bucket["payment_count"]) + 1
        bucket["total_received"] = float(bucket["total_received"]) + float(item.received_amount or 0)
        bucket["last_received_at"] = item.occurred_at

    account_summaries = [
        BillingReceiptAccountSummaryOut(
            receipt_account=account_name,
            payment_count=int(values["payment_count"]),
            total_received=float(values["total_received"]),
            last_received_at=values["last_received_at"],
        )
        for account_name, values in sorted(
            account_buckets.items(),
            key=lambda item: (-float(item[1]["total_received"]), item[0]),
        )
    ]

    return BillingReceiptAccountLedgerOut(
        receipt_account=normalized_account or None,
        date_from=date_from,
        date_to=date_to,
        total_received=float(sum(item.received_amount for item in entries)),
        payment_count=len(entries),
        account_summaries=account_summaries,
        entries=entries,
    )


@router.get("/summary")
def billing_summary(
    keyword: Optional[str] = Query(default=None),
    customer_id: Optional[int] = Query(default=None),
    receipt_account: Optional[str] = Query(default=None),
    billing_month: Optional[str] = Query(default=None),
    contact_name: Optional[str] = Query(default=None),
    payment_method: Optional[str] = Query(default=None),
    status_value: Optional[str] = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    has_billing_read_grant = False
    if current_user.role == "ACCOUNTANT":
        has_billing_read_grant = has_module_read_grant(db, current_user.id, "BILLING")

    records = db.execute(
        _apply_accountant_scope(
            select(BillingRecord).options(
                selectinload(BillingRecord.activities),
                selectinload(BillingRecord.customer),
            ),
            db,
            current_user,
            has_billing_read_grant,
        )
        .order_by(BillingRecord.serial_no.asc(), BillingRecord.id.asc())
    ).scalars().all()

    filtered_records = [
        item
        for item in records
        if _record_matches_filters(
            item,
            keyword=keyword,
            customer_id=customer_id,
            receipt_account=receipt_account,
            billing_month=billing_month,
            contact_name=contact_name,
            payment_method=payment_method,
            status_value=status_value,
        )
    ]

    payment_method_buckets: dict[str, int] = {}
    status_buckets: dict[str, int] = {}
    for record in filtered_records:
        method_name = _normalize_payment_method(record.payment_method)
        payment_method_buckets[method_name] = payment_method_buckets.get(method_name, 0) + 1
        status_buckets[record.status] = status_buckets.get(record.status, 0) + 1

    receipt_account_distribution: list[dict[str, object]] = []
    if current_user.role in {"OWNER", "ADMIN", "MANAGER"}:
        account_totals: dict[str, dict[str, object]] = {}
        counted_payment_ids: set[int] = set()

        for record in filtered_records:
            for activity in record.activities:
                if activity.activity_type != "PAYMENT" or float(activity.amount or 0) <= 0:
                    continue
                account_name = _normalize_receipt_account(activity.receipt_account)
                if receipt_account and not _matches_receipt_account(account_name, receipt_account):
                    continue

                bucket = account_totals.setdefault(
                    account_name,
                    {"payment_count": 0, "total_amount": 0.0},
                )

                if activity.payment_id:
                    bucket["total_amount"] = float(bucket["total_amount"]) + float(activity.amount or 0)
                    if activity.payment_id not in counted_payment_ids:
                        counted_payment_ids.add(activity.payment_id)
                        bucket["payment_count"] = int(bucket["payment_count"]) + 1
                    continue

                bucket["payment_count"] = int(bucket["payment_count"]) + 1
                bucket["total_amount"] = float(bucket["total_amount"]) + float(activity.amount or 0)

        receipt_account_distribution = [
            {
                "receipt_account": account_name,
                "payment_count": int(values["payment_count"]),
                "total_amount": float(values["total_amount"]),
            }
            for account_name, values in sorted(
                account_totals.items(),
                key=lambda item: (-float(item[1]["total_amount"]), item[0]),
            )
        ]

    return {
        "total_records": len(filtered_records),
        "total_fee": float(sum(float(item.total_fee or 0) for item in filtered_records)),
        "total_monthly_fee": float(sum(float(item.monthly_fee or 0) for item in filtered_records)),
        "payment_method_distribution": [
            {"payment_method": key, "count": value}
            for key, value in sorted(payment_method_buckets.items(), key=lambda item: (-item[1], item[0]))
        ],
        "status_distribution": [
            {"status": key, "count": value}
            for key, value in sorted(status_buckets.items(), key=lambda item: (-item[1], item[0]))
        ],
        "receipt_account_distribution": receipt_account_distribution,
    }


@router.get("/{record_id}/assignees", response_model=list[BillingAssignmentOut])
def list_billing_assignees(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = _get_record_or_404(db, record_id)
    _ensure_billing_access(record, db, current_user, for_write=False)

    assignments = db.execute(
        select(BillingAssignment)
        .where(BillingAssignment.billing_record_id == record.id)
        .order_by(BillingAssignment.is_active.desc(), BillingAssignment.id.desc())
    ).scalars().all()
    return assignments


@router.post(
    "/{record_id}/assignees",
    response_model=BillingAssignmentOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles("OWNER", "ADMIN", "MANAGER"))],
)
def create_billing_assignee(
    record_id: int,
    payload: BillingAssignmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = _get_record_or_404(db, record_id)
    _ensure_billing_access(record, db, current_user, for_write=True)
    assignee = db.execute(select(User).where(User.id == payload.assignee_user_id)).scalar_one_or_none()
    if assignee is None or not assignee.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Assignee not found or inactive")
    if assignee.role == "OWNER":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Owner cannot be assigned as executor")

    existing_active = db.execute(
        select(BillingAssignment.id).where(
            BillingAssignment.billing_record_id == record.id,
            BillingAssignment.assignee_user_id == payload.assignee_user_id,
            BillingAssignment.is_active.is_(True),
        )
    ).scalar_one_or_none()
    if existing_active is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Assignee already exists")

    assignment = BillingAssignment(
        billing_record_id=record.id,
        assignee_user_id=payload.assignee_user_id,
        assignment_role=payload.assignment_role,
        is_active=True,
        note=(payload.note or "").strip(),
        created_by_user_id=current_user.id,
    )
    db.add(assignment)
    write_operation_log(
        db,
        actor_id=current_user.id,
        action="BILLING_ASSIGNMENT_CREATED",
        entity_type="BILLING_ASSIGNMENT",
        entity_id=record.id,
        detail=f"record_id={record.id},assignee={assignee.username},role={assignment.assignment_role}",
    )
    db.commit()
    db.refresh(assignment)
    return assignment


@router.get("/{record_id}/execution-logs", response_model=list[BillingExecutionLogOut])
def list_billing_execution_logs(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = _get_record_or_404(db, record_id)
    _ensure_billing_access(record, db, current_user, for_write=False)

    logs = db.execute(
        select(BillingExecutionLog)
        .where(BillingExecutionLog.billing_record_id == record.id)
        .order_by(BillingExecutionLog.occurred_at.desc(), BillingExecutionLog.id.desc())
    ).scalars().all()
    return logs


@router.post("/{record_id}/execution-logs", response_model=BillingExecutionLogOut, status_code=status.HTTP_201_CREATED)
def create_billing_execution_log(
    record_id: int,
    payload: BillingExecutionLogCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = _get_record_or_404(db, record_id)
    _ensure_execution_log_write_access(record, db, current_user)
    if not payload.content.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Execution content is required")

    log = BillingExecutionLog(
        billing_record_id=record.id,
        occurred_at=payload.occurred_at,
        actor_id=current_user.id,
        progress_type=payload.progress_type,
        content=payload.content.strip(),
        next_action=(payload.next_action or "").strip(),
        due_date=payload.due_date,
        note=(payload.note or "").strip(),
    )
    db.add(log)
    write_operation_log(
        db,
        actor_id=current_user.id,
        action="BILLING_EXECUTION_LOG_CREATED",
        entity_type="BILLING_EXECUTION_LOG",
        entity_id=record.id,
        detail=f"type={log.progress_type},occurred_at={log.occurred_at}",
    )
    db.commit()
    db.refresh(log)
    return log


@router.patch(
    "/{record_id}/assignees/{assignment_id}",
    response_model=BillingAssignmentOut,
    dependencies=[Depends(require_roles("OWNER", "ADMIN", "MANAGER"))],
)
def update_billing_assignee(
    record_id: int,
    assignment_id: int,
    payload: BillingAssignmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = _get_record_or_404(db, record_id)
    _ensure_billing_access(record, db, current_user, for_write=True)
    assignment = db.execute(
        select(BillingAssignment).where(
            BillingAssignment.id == assignment_id,
            BillingAssignment.billing_record_id == record_id,
        )
    ).scalar_one_or_none()
    if assignment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Billing assignment not found")

    if payload.assignment_role is not None:
        assignment.assignment_role = payload.assignment_role
    if payload.is_active is not None:
        assignment.is_active = payload.is_active
    if payload.note is not None:
        assignment.note = payload.note.strip()

    write_operation_log(
        db,
        actor_id=current_user.id,
        action="BILLING_ASSIGNMENT_UPDATED",
        entity_type="BILLING_ASSIGNMENT",
        entity_id=assignment.id,
        detail=f"is_active={assignment.is_active},role={assignment.assignment_role}",
    )
    db.commit()
    db.refresh(assignment)
    return assignment


@router.get("/{record_id}/activities", response_model=list[BillingActivityOut])
def list_billing_activities(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = _get_record_or_404(db, record_id)
    _ensure_billing_access(record, db, current_user, for_write=False)

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
    record = _get_record_or_404(db, record_id)
    _ensure_billing_access(record, db, current_user, for_write=True)

    if payload.activity_type == "PAYMENT" and payload.amount <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment amount must be greater than zero")
    if payload.activity_type == "REMINDER" and payload.amount != 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reminder amount must be zero")

    activity = BillingActivity(
        billing_record_id=record.id,
        activity_type=payload.activity_type,
        occurred_at=payload.occurred_at,
        actor_id=current_user.id,
        payment_id=None,
        amount=payload.amount if payload.activity_type == "PAYMENT" else 0,
        payment_nature=payload.payment_nature,
        receipt_account=_normalize_receipt_account(payload.receipt_account) if payload.activity_type == "PAYMENT" else "",
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
        detail=f"type={payload.activity_type},amount={activity.amount},receipt_account={activity.receipt_account}",
    )
    db.commit()
    db.refresh(activity)
    return activity
