from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import exists, false, or_, select

from app.models import BillingAssignment, BillingRecord, Customer


def _normalize_user_ids(user_ids: Iterable[int]) -> list[int]:
    normalized = [int(item) for item in user_ids if int(item or 0) > 0]
    return sorted(set(normalized))


def customer_owned_by_user_condition(user_id: int):
    user_token = int(user_id or 0)
    return or_(
        Customer.responsible_user_id == user_token,
        Customer.assigned_accountant_id == user_token,
    )


def customer_owned_by_any_condition(user_ids: Iterable[int]):
    normalized = _normalize_user_ids(user_ids)
    if not normalized:
        return false()
    return or_(
        Customer.responsible_user_id.in_(normalized),
        Customer.assigned_accountant_id.in_(normalized),
    )


def billing_assignment_exists_condition(user_id: int):
    return exists(
        select(BillingAssignment.id).where(
            BillingAssignment.billing_record_id == BillingRecord.id,
            BillingAssignment.assignee_user_id == int(user_id or 0),
            BillingAssignment.is_active.is_(True),
        )
    )
