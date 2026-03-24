from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User


def get_manager_subordinate_ids(db: Session, manager_user_id: int, *, active_only: bool = False) -> list[int]:
    stmt = select(User.id).where(User.manager_user_id == manager_user_id)
    if active_only:
        stmt = stmt.where(User.is_active.is_(True))
    return list(db.execute(stmt.order_by(User.id.asc())).scalars().all())


def is_manager_of(db: Session, manager_user_id: int, user_id: int) -> bool:
    if manager_user_id <= 0 or user_id <= 0:
        return False
    stmt = select(User.id).where(
        User.id == user_id,
        User.manager_user_id == manager_user_id,
    )
    return db.execute(stmt).scalar_one_or_none() is not None


def ensure_manager_scope(target_user_id: int, subordinate_user_ids: Iterable[int]) -> bool:
    return int(target_user_id or 0) in {int(item) for item in subordinate_user_ids}
