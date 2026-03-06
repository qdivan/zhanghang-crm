from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, aliased

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import BillingRecord, Customer, Lead, TodoItem, User
from app.schemas.dashboard import DashboardSummaryOut, SystemTodoOut
from app.services.data_access import has_module_read_grant

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

SYSTEM_TODO_SOON_DAYS = 15
SYSTEM_RENEW_SOON_DAYS = 30


def _month_end(target_date: date) -> date:
    month_start = target_date.replace(day=1)
    next_month = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1)
    return next_month - timedelta(days=1)


def _priority_from_due(due_date: Optional[date], today: date) -> str:
    if due_date is None:
        return "LOW"
    if due_date < today:
        return "HIGH"
    if due_date <= today + timedelta(days=3):
        return "HIGH"
    if due_date <= today + timedelta(days=SYSTEM_TODO_SOON_DAYS):
        return "MEDIUM"
    return "LOW"


def _parse_due_month(value: str) -> Optional[date]:
    text = (value or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _apply_lead_scope(stmt, current_user: User):
    if current_user.role != "ACCOUNTANT":
        return stmt
    return stmt.where(
        or_(
            Lead.owner_id == current_user.id,
            Lead.customer.has(Customer.assigned_accountant_id == current_user.id),
        )
    )


def _apply_customer_scope(stmt, db: Session, current_user: User):
    if current_user.role != "ACCOUNTANT":
        return stmt
    if has_module_read_grant(db, current_user.id, "CUSTOMER"):
        return stmt
    return stmt.where(Customer.assigned_accountant_id == current_user.id)


def _apply_billing_scope(stmt, db: Session, current_user: User):
    if current_user.role != "ACCOUNTANT":
        return stmt
    if has_module_read_grant(db, current_user.id, "BILLING"):
        return stmt
    return stmt.where(BillingRecord.customer.has(Customer.assigned_accountant_id == current_user.id))


def _apply_billing_system_todo_scope(stmt, current_user: User):
    if current_user.role != "ACCOUNTANT":
        return stmt
    # 系统催收待办仅面向“自己负责客户”，不跟随临时只读授权放大范围。
    return stmt.where(Customer.assigned_accountant_id == current_user.id)


def _build_system_todos(db: Session, current_user: User, *, limit: int = 50) -> list[SystemTodoOut]:
    today = date.today()
    month_end = _month_end(today)
    due_window_end = today + timedelta(days=SYSTEM_TODO_SOON_DAYS)
    renew_window_end = today + timedelta(days=SYSTEM_RENEW_SOON_DAYS)
    renew_window_start = today - timedelta(days=7)

    items: list[SystemTodoOut] = []

    lead_owner = aliased(User)
    lead_accountant = aliased(User)
    lead_stmt = (
        select(Lead, lead_owner.username, Customer.assigned_accountant_id, lead_accountant.username)
        .join(lead_owner, Lead.owner_id == lead_owner.id)
        .outerjoin(Customer, Customer.source_lead_id == Lead.id)
        .outerjoin(lead_accountant, Customer.assigned_accountant_id == lead_accountant.id)
        .where(
            Lead.status.in_(["NEW", "FOLLOWING"]),
            Lead.next_reminder_at.is_not(None),
            Lead.next_reminder_at <= month_end,
        )
        .order_by(Lead.next_reminder_at.asc(), Lead.id.asc())
    )
    lead_rows = db.execute(_apply_lead_scope(lead_stmt, current_user)).all()
    for lead, owner_username, assigned_accountant_id, accountant_username in lead_rows:
        due_date = lead.next_reminder_at
        assignee_user_id = assigned_accountant_id or lead.owner_id
        assignee_username = accountant_username or owner_username
        items.append(
            SystemTodoOut(
                id=f"lead:{lead.id}",
                module="LEAD",
                priority=_priority_from_due(due_date, today),
                title=f"跟进线索：{lead.name}",
                description=f"本月需完成跟进，当前状态：{lead.status}",
                due_date=due_date,
                action_path=f"/leads/{lead.id}",
                action_label="查看线索",
                assignee_user_id=assignee_user_id,
                assignee_username=assignee_username,
            )
        )

    billing_accountant = aliased(User)
    billing_stmt = (
        select(
            BillingRecord.id,
            BillingRecord.customer_name,
            BillingRecord.due_month,
            BillingRecord.outstanding_amount,
            Customer.assigned_accountant_id,
            billing_accountant.username,
        )
        .outerjoin(Customer, BillingRecord.customer_id == Customer.id)
        .outerjoin(billing_accountant, Customer.assigned_accountant_id == billing_accountant.id)
        .where(BillingRecord.status != "CLEARED", BillingRecord.outstanding_amount > 0)
        .order_by(BillingRecord.id.asc())
    )
    billing_rows = db.execute(_apply_billing_system_todo_scope(billing_stmt, current_user)).all()
    for record_id, customer_name, due_month, outstanding_amount, assignee_user_id, assignee_username in billing_rows:
        due_date = _parse_due_month(due_month)
        if due_date is None or due_date > due_window_end:
            continue
        due_label = "已到期" if due_date < today else "即将到期"
        items.append(
            SystemTodoOut(
                id=f"billing:{record_id}",
                module="BILLING",
                priority=_priority_from_due(due_date, today),
                title=f"{due_label}催收：{customer_name}",
                description=f"到期日 {due_date.isoformat()}，当前未收 {float(outstanding_amount):.2f}",
                due_date=due_date,
                action_path="/billing",
                action_label="查看收费台账",
                assignee_user_id=assignee_user_id,
                assignee_username=assignee_username or "-",
            )
        )

    renew_stmt = (
        select(
            BillingRecord.id,
            BillingRecord.customer_name,
            BillingRecord.due_month,
            Customer.assigned_accountant_id,
            billing_accountant.username,
        )
        .outerjoin(Customer, BillingRecord.customer_id == Customer.id)
        .outerjoin(billing_accountant, Customer.assigned_accountant_id == billing_accountant.id)
        .where(BillingRecord.charge_mode == "PERIODIC")
        .order_by(BillingRecord.id.asc())
    )
    renew_rows = db.execute(_apply_billing_system_todo_scope(renew_stmt, current_user)).all()
    for record_id, customer_name, due_month, assignee_user_id, assignee_username in renew_rows:
        due_date = _parse_due_month(due_month)
        if due_date is None or due_date < renew_window_start or due_date > renew_window_end:
            continue
        items.append(
            SystemTodoOut(
                id=f"renew:{record_id}",
                module="BILLING",
                priority=_priority_from_due(due_date, today),
                title=f"续费确认：{customer_name}",
                description=f"合同到期日 {due_date.isoformat()}，请确认是否续费并生成新周期",
                due_date=due_date,
                action_path=f"/billing?action=renew&record_id={record_id}",
                action_label="一键续费",
                assignee_user_id=assignee_user_id,
                assignee_username=assignee_username or "-",
            )
        )

    priority_rank = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    items.sort(
        key=lambda item: (
            priority_rank.get(item.priority, 9),
            item.due_date or date.max,
            item.id,
        )
    )
    return items[:limit]


@router.get("/summary", response_model=DashboardSummaryOut)
def get_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    today = date.today()

    lead_new_count = db.execute(
        _apply_lead_scope(
            select(func.count(Lead.id)).where(Lead.status == "NEW"),
            current_user,
        )
    ).scalar_one()
    lead_following_count = db.execute(
        _apply_lead_scope(
            select(func.count(Lead.id)).where(Lead.status == "FOLLOWING"),
            current_user,
        )
    ).scalar_one()

    customer_count = db.execute(
        _apply_customer_scope(select(func.count(Customer.id)), db, current_user)
    ).scalar_one()

    billing_record_count = db.execute(
        _apply_billing_scope(select(func.count(BillingRecord.id)), db, current_user)
    ).scalar_one()
    outstanding_amount_total = db.execute(
        _apply_billing_scope(
            select(func.sum(BillingRecord.outstanding_amount)).where(BillingRecord.status != "CLEARED"),
            db,
            current_user,
        )
    ).scalar() or 0

    manual_open_todo_count = db.execute(
        select(func.count(TodoItem.id)).where(
            TodoItem.assignee_user_id == current_user.id,
            TodoItem.status == "OPEN",
        )
    ).scalar_one()

    system_todo_count = len(_build_system_todos(db, current_user, limit=500))

    return DashboardSummaryOut(
        month=today.strftime("%Y-%m"),
        lead_new_count=int(lead_new_count or 0),
        lead_following_count=int(lead_following_count or 0),
        customer_count=int(customer_count or 0),
        billing_record_count=int(billing_record_count or 0),
        outstanding_amount_total=float(outstanding_amount_total),
        manual_open_todo_count=int(manual_open_todo_count or 0),
        system_todo_count=system_todo_count,
    )


@router.get("/system-todos", response_model=list[SystemTodoOut])
def list_system_todos(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _build_system_todos(db, current_user, limit=limit)
