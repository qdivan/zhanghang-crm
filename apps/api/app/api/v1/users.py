from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.security import hash_password
from app.db.session import get_db
from app.models import (
    BillingActivity,
    BillingAssignment,
    BillingExecutionLog,
    BillingPayment,
    Customer,
    DataAccessGrant,
    Lead,
    OperationLog,
    TodoItem,
    User,
)
from app.schemas.auth import UserOut
from app.schemas.user_admin import UserCreate, UserUpdate
from app.services.audit import write_operation_log
from app.services.org_scope import get_manager_subordinate_ids
from app.services.soft_delete import active_filter, deleted_filter, mark_deleted

router = APIRouter(prefix="/users", tags=["users"])


def _normalize_username(username: str) -> str:
    normalized = username.strip()
    if not normalized:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户名不能为空")
    return normalized


def _ensure_owner_scope(current_user: User, target_user_role: str) -> None:
    if current_user.role == "OWNER" and target_user_role == "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="老板不能管理管理员账号",
        )


def _resolve_manager_user_id(
    db: Session,
    manager_user_id: Optional[int],
    *,
    target_role: str,
) -> Optional[int]:
    if target_role != "ACCOUNTANT":
        return None
    if manager_user_id is None:
        return None
    manager = db.execute(select(User).where(User.id == manager_user_id, active_filter(User))).scalar_one_or_none()
    if manager is None or not manager.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="直属经理不存在或已停用")
    if manager.role != "MANAGER":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="直属经理必须是部门经理")
    return manager.id


def _count_direct_reports(db: Session, user_id: int) -> int:
    return int(
        db.execute(
            select(func.count(User.id)).where(User.manager_user_id == user_id, active_filter(User))
        ).scalar_one()
        or 0
    )


def _get_user_or_404(db: Session, user_id: int) -> User:
    user = db.execute(select(User).where(User.id == user_id, active_filter(User))).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    return user


def _count_user_dependencies(db: Session, user_id: int) -> dict[str, int]:
    lead_count = db.execute(
        select(func.count(Lead.id)).where(Lead.owner_id == user_id),
    ).scalar_one()
    customer_count = db.execute(
        select(func.count(Customer.id)).where(Customer.assigned_accountant_id == user_id),
    ).scalar_one()
    activity_count = db.execute(
        select(func.count(BillingActivity.id)).where(BillingActivity.actor_id == user_id),
    ).scalar_one()
    assignment_count = db.execute(
        select(func.count(BillingAssignment.id)).where(BillingAssignment.assignee_user_id == user_id),
    ).scalar_one()
    execution_log_count = db.execute(
        select(func.count(BillingExecutionLog.id)).where(BillingExecutionLog.actor_id == user_id),
    ).scalar_one()
    payment_count = db.execute(
        select(func.count(BillingPayment.id)).where(BillingPayment.created_by_user_id == user_id),
    ).scalar_one()
    operation_log_count = db.execute(
        select(func.count(OperationLog.id)).where(OperationLog.actor_id == user_id),
    ).scalar_one()
    data_grant_count = db.execute(
        select(func.count(DataAccessGrant.id)).where(DataAccessGrant.grantee_user_id == user_id, active_filter(DataAccessGrant)),
    ).scalar_one()
    todo_count = db.execute(
        select(func.count(TodoItem.id)).where(
            or_(
                TodoItem.assignee_user_id == user_id,
                TodoItem.created_by_user_id == user_id,
            )
        ),
    ).scalar_one()
    direct_report_count = _count_direct_reports(db, user_id)
    return {
        "线索": int(lead_count or 0),
        "客户": int(customer_count or 0),
        "催收收款日志": int(activity_count or 0),
        "执行进度日志": int(execution_log_count or 0),
        "收款分摊单": int(payment_count or 0),
        "执行分派": int(assignment_count or 0),
        "操作日志": int(operation_log_count or 0),
        "数据授权": int(data_grant_count or 0),
        "待办": int(todo_count or 0),
        "下属": int(direct_report_count or 0),
    }


@router.get("", response_model=list[UserOut], dependencies=[Depends(require_roles("OWNER", "ADMIN", "MANAGER"))])
def list_users(
    role: Optional[str] = Query(default=None),
    keyword: Optional[str] = Query(default=None),
    include_inactive: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(User).order_by(User.id.asc())
    stmt = stmt.where(active_filter(User))
    if not include_inactive:
        stmt = stmt.where(User.is_active.is_(True))
    if role:
        stmt = stmt.where(User.role == role)
    if keyword:
        key = f"%{keyword.strip()}%"
        stmt = stmt.where(or_(User.username.ilike(key), User.role.ilike(key)))
    if current_user.role == "MANAGER":
        stmt = stmt.where(User.id.in_(get_manager_subordinate_ids(db, current_user.id)))
    elif current_user.role == "OWNER":
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
        if existing.is_deleted:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该用户名已在回收站，可先恢复")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户名已存在")

    user = User(
        username=username,
        password_hash=hash_password(payload.password),
        auth_source="LOCAL",
        role=payload.role,
        manager_user_id=_resolve_manager_user_id(
            db,
            payload.manager_user_id,
            target_role=payload.role,
        ),
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
    provided_fields = set(payload.model_fields_set)

    if payload.role is not None:
        _ensure_owner_scope(current_user, payload.role)
        if current_user.id == target_user.id and payload.role != target_user.role:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能修改自己的角色")
        if target_user.role == "MANAGER" and payload.role != "MANAGER" and _count_direct_reports(db, target_user.id) > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="该部门经理仍有关联下属，不能直接改成其他角色",
            )
        old_role = target_user.role
        target_user.role = payload.role
    else:
        old_role = target_user.role

    if payload.username is not None:
        username = _normalize_username(payload.username)
        existing = (
            db.execute(select(User).where(User.username == username, User.id != target_user.id)).scalar_one_or_none()
        )
        if existing is not None:
            if existing.is_deleted:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该用户名已在回收站，可先恢复")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户名已存在")
        old_username = target_user.username
        target_user.username = username
    else:
        old_username = target_user.username

    password_changed = False
    if payload.password is not None:
        target_user.password_hash = hash_password(payload.password)
        password_changed = True

    if payload.is_active is not None:
        if current_user.id == target_user.id and payload.is_active is False:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能停用当前登录账号")
        if target_user.role == "MANAGER" and payload.is_active is False and _count_direct_reports(db, target_user.id) > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="该部门经理仍有关联下属，不能直接停用",
            )
        old_active = target_user.is_active
        target_user.is_active = payload.is_active
    else:
        old_active = target_user.is_active

    next_role = target_user.role
    old_manager_user_id = target_user.manager_user_id
    if "role" in provided_fields or "manager_user_id" in provided_fields:
        target_user.manager_user_id = _resolve_manager_user_id(
            db,
            payload.manager_user_id,
            target_role=next_role,
        )
    if target_user.id == target_user.manager_user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="直属经理不能设置为自己")

    change_items: list[str] = []
    if old_username != target_user.username:
        change_items.append(f"username:{old_username}->{target_user.username}")
    if old_role != target_user.role:
        change_items.append(f"role:{old_role}->{target_user.role}")
    if old_active != target_user.is_active:
        change_items.append(
            f"is_active:{'启用' if old_active else '停用'}->{'启用' if target_user.is_active else '停用'}"
        )
    if old_manager_user_id != target_user.manager_user_id:
        change_items.append(
            f"manager_user_id:{old_manager_user_id or '-'}->{target_user.manager_user_id or '-'}"
        )
    if password_changed:
        change_items.append("password:已修改")

    write_operation_log(
        db,
        actor_id=current_user.id,
        action="USER_UPDATED",
        entity_type="USER",
        entity_id=target_user.id,
        detail=f"changes={'; '.join(change_items) if change_items else 'none'}",
    )
    db.commit()
    db.refresh(target_user)
    return target_user


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles("OWNER", "ADMIN"))],
)
def delete_user(
    user_id: int,
    confirm_name: str = Query(default=""),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    target_user = _get_user_or_404(db, user_id)
    _ensure_owner_scope(current_user, target_user.role)

    if current_user.id == target_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能删除当前登录账号")
    if target_user.auth_source == "LDAP":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="LDAP账号请在LDAP中停用或删除",
        )

    dependencies = _count_user_dependencies(db, target_user.id)
    blocking_items = [f"{name}={count}" for name, count in dependencies.items() if count > 0]
    if blocking_items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"该账号存在关联数据，无法删除（{', '.join(blocking_items)}）",
        )

    username = target_user.username
    if confirm_name.strip() != username:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="确认名称不匹配")
    mark_deleted(target_user, current_user.id)
    write_operation_log(
        db,
        actor_id=current_user.id,
        action="USER_DELETED",
        entity_type="USER",
        entity_id=user_id,
        detail=f"username={username}",
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
