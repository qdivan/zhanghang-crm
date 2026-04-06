from datetime import datetime
from typing import Optional

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.models import DataAccessGrant
from app.services.soft_delete import active_filter


def has_module_read_grant(db: Session, user_id: int, module: str) -> bool:
    now = datetime.utcnow()
    stmt = select(DataAccessGrant.id).where(
        active_filter(DataAccessGrant),
        DataAccessGrant.grantee_user_id == user_id,
        DataAccessGrant.module == module,
        DataAccessGrant.is_active.is_(True),
        or_(DataAccessGrant.starts_at.is_(None), DataAccessGrant.starts_at <= now),
        or_(DataAccessGrant.ends_at.is_(None), DataAccessGrant.ends_at >= now),
    )
    return db.execute(stmt).scalar_one_or_none() is not None


def has_overlapping_active_grant(
    db: Session,
    grantee_user_id: int,
    module: str,
    starts_at: Optional[datetime],
    ends_at: Optional[datetime],
    exclude_grant_id: Optional[int] = None,
) -> bool:
    # 时间重叠判断：
    # [a_start, a_end] 与 [b_start, b_end] 不重叠 <=> a_end < b_start OR b_end < a_start
    # 这里将 None 视为无限边界。
    query_start = starts_at or datetime(1970, 1, 1)
    query_end = ends_at or datetime(9999, 12, 31, 23, 59, 59)

    stmt = select(DataAccessGrant.id).where(
        active_filter(DataAccessGrant),
        DataAccessGrant.grantee_user_id == grantee_user_id,
        DataAccessGrant.module == module,
        DataAccessGrant.is_active.is_(True),
        and_(
            or_(DataAccessGrant.ends_at.is_(None), DataAccessGrant.ends_at >= query_start),
            or_(DataAccessGrant.starts_at.is_(None), DataAccessGrant.starts_at <= query_end),
        ),
    )
    if exclude_grant_id is not None:
        stmt = stmt.where(DataAccessGrant.id != exclude_grant_id)
    return db.execute(stmt).scalar_one_or_none() is not None
