from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.security import hash_password
from app.db.session import get_db
from app.models import User
from app.schemas.auth import UserOut
from app.schemas.user_admin import UserCreate, UserUpdate
from app.services.audit import write_operation_log

router = APIRouter(prefix="/users", tags=["users"])


def _normalize_username(username: str) -> str:
    normalized = username.strip()
    if not normalized:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username cannot be empty")
    return normalized


def _ensure_owner_scope(current_user: User, target_user_role: str) -> None:
    if current_user.role == "OWNER" and target_user_role == "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Owner cannot manage admin users",
        )


def _get_user_or_404(db: Session, user_id: int) -> User:
    user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.get("", response_model=list[UserOut], dependencies=[Depends(require_roles("OWNER", "ADMIN"))])
def list_users(
    role: Optional[str] = Query(default=None),
    keyword: Optional[str] = Query(default=None),
    include_inactive: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(User).order_by(User.id.asc())
    if not include_inactive:
        stmt = stmt.where(User.is_active.is_(True))
    if role:
        stmt = stmt.where(User.role == role)
    if keyword:
        key = f"%{keyword.strip()}%"
        stmt = stmt.where(or_(User.username.ilike(key), User.role.ilike(key)))
    if current_user.role == "OWNER":
        stmt = stmt.where(User.role != "ADMIN")
    return db.execute(stmt).scalars().all()


@router.post(
    "",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles("OWNER", "ADMIN"))],
)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_owner_scope(current_user, payload.role)

    username = _normalize_username(payload.username)
    existing = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")

    user = User(
        username=username,
        password_hash=hash_password(payload.password),
        auth_source="LOCAL",
        role=payload.role,
        is_active=payload.is_active,
    )
    write_operation_log(
        db,
        actor_id=current_user.id,
        action="USER_CREATED",
        entity_type="USER",
        entity_id=username,
        detail=f"role={payload.role},active={payload.is_active}",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.patch(
    "/{user_id}",
    response_model=UserOut,
    dependencies=[Depends(require_roles("OWNER", "ADMIN"))],
)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    target_user = _get_user_or_404(db, user_id)
    _ensure_owner_scope(current_user, target_user.role)

    if payload.role is not None:
        _ensure_owner_scope(current_user, payload.role)
        if current_user.id == target_user.id and payload.role != target_user.role:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot change your own role")
        target_user.role = payload.role

    if payload.username is not None:
        username = _normalize_username(payload.username)
        existing = (
            db.execute(select(User).where(User.username == username, User.id != target_user.id)).scalar_one_or_none()
        )
        if existing is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")
        target_user.username = username

    if payload.password is not None:
        target_user.password_hash = hash_password(payload.password)

    if payload.is_active is not None:
        if current_user.id == target_user.id and payload.is_active is False:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot deactivate yourself")
        target_user.is_active = payload.is_active

    write_operation_log(
        db,
        actor_id=current_user.id,
        action="USER_UPDATED",
        entity_type="USER",
        entity_id=target_user.id,
        detail=f"username={target_user.username}",
    )
    db.commit()
    db.refresh(target_user)
    return target_user
