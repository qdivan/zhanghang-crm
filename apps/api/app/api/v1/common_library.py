from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import CommonLibraryItem, User
from app.schemas.common_library import (
    CommonLibraryItemCreate,
    CommonLibraryItemOut,
    CommonLibraryItemUpdate,
)
from app.services.audit import write_operation_log

router = APIRouter(prefix="/common-library-items", tags=["common-library-items"])


@router.get("", response_model=list[CommonLibraryItemOut])
def list_common_library_items(
    module_type: Optional[str] = Query(default=None),
    visibility: Optional[str] = Query(default=None),
    keyword: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    del current_user
    stmt = select(CommonLibraryItem).order_by(CommonLibraryItem.updated_at.desc(), CommonLibraryItem.id.desc())
    if module_type:
        stmt = stmt.where(CommonLibraryItem.module_type == module_type)
    if visibility:
        stmt = stmt.where(CommonLibraryItem.visibility == visibility.upper())
    if keyword:
        key = f"%{keyword.strip()}%"
        stmt = stmt.where(
            or_(
                CommonLibraryItem.category.ilike(key),
                CommonLibraryItem.title.ilike(key),
                CommonLibraryItem.content.ilike(key),
                CommonLibraryItem.phone.ilike(key),
                CommonLibraryItem.address.ilike(key),
                CommonLibraryItem.notes.ilike(key),
            )
        )
    return db.execute(stmt).scalars().all()


@router.get("/public", response_model=list[CommonLibraryItemOut])
def list_public_common_library_items(
    module_type: Optional[str] = Query(default=None),
    keyword: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    stmt = (
        select(CommonLibraryItem)
        .where(CommonLibraryItem.visibility == "PUBLIC")
        .order_by(CommonLibraryItem.updated_at.desc(), CommonLibraryItem.id.desc())
    )
    if module_type:
        stmt = stmt.where(CommonLibraryItem.module_type == module_type)
    if keyword:
        key = f"%{keyword.strip()}%"
        stmt = stmt.where(
            or_(
                CommonLibraryItem.category.ilike(key),
                CommonLibraryItem.title.ilike(key),
                CommonLibraryItem.content.ilike(key),
                CommonLibraryItem.phone.ilike(key),
                CommonLibraryItem.address.ilike(key),
                CommonLibraryItem.notes.ilike(key),
            )
        )
    return db.execute(stmt).scalars().all()


@router.post("", response_model=CommonLibraryItemOut, status_code=status.HTTP_201_CREATED)
def create_common_library_item(
    payload: CommonLibraryItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = payload.model_dump()
    for key, value in data.items():
        if isinstance(value, str):
            data[key] = value.strip()
    if "visibility" in data:
        data["visibility"] = data["visibility"].upper() or "INTERNAL"

    item = CommonLibraryItem(**data)
    db.add(item)
    write_operation_log(
        db,
        actor_id=current_user.id,
        action="COMMON_LIBRARY_ITEM_CREATED",
        entity_type="COMMON_LIBRARY",
        entity_id=payload.module_type,
        detail=payload.title or payload.category,
    )
    db.commit()
    db.refresh(item)
    return item


@router.patch("/{item_id}", response_model=CommonLibraryItemOut)
def update_common_library_item(
    item_id: int,
    payload: CommonLibraryItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = db.execute(select(CommonLibraryItem).where(CommonLibraryItem.id == item_id)).scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="常用资料不存在")

    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="没有可更新的字段")

    for key, value in update_data.items():
        if value is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"字段 {key} 不能为空")
        if isinstance(value, str):
            value = value.strip()
        if key == "visibility":
            value = value.upper() or "INTERNAL"
        setattr(item, key, value)
    item.updated_at = datetime.utcnow()

    write_operation_log(
        db,
        actor_id=current_user.id,
        action="COMMON_LIBRARY_ITEM_UPDATED",
        entity_type="COMMON_LIBRARY",
        entity_id=item.id,
        detail=item.title or item.category,
    )
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_common_library_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = db.execute(select(CommonLibraryItem).where(CommonLibraryItem.id == item_id)).scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="常用资料不存在")

    title = item.title or item.category
    db.delete(item)
    write_operation_log(
        db,
        actor_id=current_user.id,
        action="COMMON_LIBRARY_ITEM_DELETED",
        entity_type="COMMON_LIBRARY",
        entity_id=item_id,
        detail=title,
    )
    db.commit()
