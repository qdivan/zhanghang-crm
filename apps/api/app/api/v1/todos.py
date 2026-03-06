from datetime import date, datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, aliased

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import TodoItem, User
from app.schemas.todo import TodoBulkUpdateResult, TodoCreate, TodoOut, TodoUpdate
from app.services.audit import write_operation_log

router = APIRouter(prefix="/todos", tags=["todos"])


def _today() -> date:
    return date.today()


def _can_manage_foreign_todo(current_user: User) -> bool:
    return current_user.role in {"OWNER", "ADMIN"}


def _resolve_target_assignee(
    requested_assignee_user_id: Optional[int],
    current_user: User,
) -> int:
    target_assignee_user_id = requested_assignee_user_id or current_user.id
    if target_assignee_user_id != current_user.id and not _can_manage_foreign_todo(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="当前账号权限不足")
    return target_assignee_user_id


def _get_user_or_400(db: Session, user_id: int) -> User:
    user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户不存在")
    return user


def _get_todo_or_404(db: Session, todo_id: int) -> TodoItem:
    todo = db.execute(select(TodoItem).where(TodoItem.id == todo_id)).scalar_one_or_none()
    if todo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="待办不存在")
    return todo


def _ensure_todo_write_access(todo: TodoItem, current_user: User) -> None:
    if _can_manage_foreign_todo(current_user):
        return
    if todo.assignee_user_id == current_user.id:
        return
    if todo.created_by_user_id == current_user.id:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="当前账号权限不足")


def _serialize_todo(todo: TodoItem, assignee_username: str, creator_username: str) -> TodoOut:
    today = _today()
    return TodoOut(
        id=todo.id,
        title=todo.title,
        description=todo.description,
        priority=todo.priority,
        due_date=todo.due_date,
        my_day_date=todo.my_day_date,
        is_in_today=todo.my_day_date == today,
        status=todo.status,
        assignee_user_id=todo.assignee_user_id,
        assignee_username=assignee_username,
        created_by_user_id=todo.created_by_user_id,
        created_by_username=creator_username,
        completed_at=todo.completed_at,
        created_at=todo.created_at,
        updated_at=todo.updated_at,
    )


def _load_todo_out(db: Session, todo_id: int) -> TodoOut:
    assignee = aliased(User)
    creator = aliased(User)
    row = db.execute(
        select(TodoItem, assignee.username, creator.username)
        .join(assignee, TodoItem.assignee_user_id == assignee.id)
        .join(creator, TodoItem.created_by_user_id == creator.id)
        .where(TodoItem.id == todo_id)
    ).one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="待办不存在")
    todo, assignee_username, creator_username = row
    return _serialize_todo(todo, assignee_username, creator_username)


@router.get("", response_model=list[TodoOut])
def list_todos(
    view: Literal["ALL", "TODAY"] = Query(default="ALL"),
    include_done: bool = Query(default=False),
    assignee_user_id: Optional[int] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    target_assignee_user_id = _resolve_target_assignee(assignee_user_id, current_user)
    today = _today()

    assignee = aliased(User)
    creator = aliased(User)
    stmt = (
        select(TodoItem, assignee.username, creator.username)
        .join(assignee, TodoItem.assignee_user_id == assignee.id)
        .join(creator, TodoItem.created_by_user_id == creator.id)
        .where(TodoItem.assignee_user_id == target_assignee_user_id)
        .limit(limit)
    )
    if view == "TODAY":
        stmt = stmt.where(
            TodoItem.status == "OPEN",
            TodoItem.my_day_date == today,
        ).order_by(TodoItem.priority.asc(), TodoItem.due_date.asc().nulls_last(), TodoItem.id.desc())
    else:
        if not include_done:
            stmt = stmt.where(TodoItem.status == "OPEN")
        stmt = stmt.order_by(TodoItem.status.asc(), TodoItem.due_date.asc().nulls_last(), TodoItem.id.desc())

    rows = db.execute(stmt).all()
    return [_serialize_todo(todo, assignee_username, creator_username) for todo, assignee_username, creator_username in rows]


@router.post("", response_model=TodoOut, status_code=status.HTTP_201_CREATED)
def create_todo(
    payload: TodoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    target_assignee_user_id = _resolve_target_assignee(payload.assignee_user_id, current_user)

    assignee = _get_user_or_400(db, target_assignee_user_id)
    todo = TodoItem(
        title=payload.title.strip(),
        description=payload.description.strip(),
        priority=payload.priority,
        due_date=payload.due_date,
        my_day_date=_today() if payload.is_in_today else None,
        status="OPEN",
        assignee_user_id=assignee.id,
        created_by_user_id=current_user.id,
    )
    db.add(todo)
    db.flush()
    write_operation_log(
        db,
        actor_id=current_user.id,
        action="TODO_CREATED",
        entity_type="TODO",
        entity_id=todo.id,
        detail=f"assignee={assignee.username},priority={todo.priority},in_today={payload.is_in_today}",
    )
    db.commit()
    return _load_todo_out(db, todo.id)


@router.patch("/{todo_id}", response_model=TodoOut)
def update_todo(
    todo_id: int,
    payload: TodoUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    todo = _get_todo_or_404(db, todo_id)
    _ensure_todo_write_access(todo, current_user)

    changed_fields: list[str] = []
    data = payload.model_dump(exclude_unset=True)
    if "title" in data:
        todo.title = (payload.title or "").strip()
        changed_fields.append("title")
    if "description" in data:
        todo.description = (payload.description or "").strip()
        changed_fields.append("description")
    if "priority" in data:
        todo.priority = payload.priority or "MEDIUM"
        changed_fields.append("priority")
    if "due_date" in data:
        todo.due_date = payload.due_date
        changed_fields.append("due_date")
    if "status" in data:
        todo.status = payload.status or "OPEN"
        todo.completed_at = datetime.utcnow() if todo.status == "DONE" else None
        changed_fields.append("status")
    if "is_in_today" in data:
        todo.my_day_date = _today() if payload.is_in_today else None
        changed_fields.append("is_in_today")

    write_operation_log(
        db,
        actor_id=current_user.id,
        action="TODO_UPDATED",
        entity_type="TODO",
        entity_id=todo.id,
        detail=f"changes={','.join(changed_fields) if changed_fields else 'none'}",
    )
    db.commit()
    return _load_todo_out(db, todo.id)


@router.post("/my-day/add-all", response_model=TodoBulkUpdateResult)
def add_all_to_my_day(
    assignee_user_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    target_assignee_user_id = _resolve_target_assignee(assignee_user_id, current_user)
    today = _today()

    todos = db.execute(
        select(TodoItem)
        .where(
            TodoItem.assignee_user_id == target_assignee_user_id,
            TodoItem.status == "OPEN",
            or_(TodoItem.my_day_date.is_(None), TodoItem.my_day_date != today),
        )
    ).scalars().all()

    for todo in todos:
        todo.my_day_date = today

    write_operation_log(
        db,
        actor_id=current_user.id,
        action="TODO_MY_DAY_BULK_ADD",
        entity_type="TODO",
        entity_id=str(target_assignee_user_id),
        detail=f"affected={len(todos)}",
    )
    db.commit()
    return TodoBulkUpdateResult(affected_count=len(todos))


@router.post("/my-day/clear", response_model=TodoBulkUpdateResult)
def clear_my_day(
    assignee_user_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    target_assignee_user_id = _resolve_target_assignee(assignee_user_id, current_user)
    today = _today()

    todos = db.execute(
        select(TodoItem)
        .where(
            TodoItem.assignee_user_id == target_assignee_user_id,
            TodoItem.my_day_date == today,
        )
    ).scalars().all()

    for todo in todos:
        todo.my_day_date = None

    write_operation_log(
        db,
        actor_id=current_user.id,
        action="TODO_MY_DAY_CLEARED",
        entity_type="TODO",
        entity_id=str(target_assignee_user_id),
        detail=f"affected={len(todos)}",
    )
    db.commit()
    return TodoBulkUpdateResult(affected_count=len(todos))


@router.delete("/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_todo(
    todo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    todo = _get_todo_or_404(db, todo_id)
    _ensure_todo_write_access(todo, current_user)
    db.delete(todo)
    write_operation_log(
        db,
        actor_id=current_user.id,
        action="TODO_DELETED",
        entity_type="TODO",
        entity_id=todo_id,
        detail="deleted",
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
