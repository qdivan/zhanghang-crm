from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import AddressResource, User
from app.schemas.address_resource import (
    AddressResourceCreate,
    AddressResourceOut,
    AddressResourceUpdate,
)
from app.services.audit import write_operation_log

router = APIRouter(prefix="/address-resources", tags=["address-resources"])


@router.get("", response_model=list[AddressResourceOut])
def list_address_resources(
    keyword: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(AddressResource).order_by(AddressResource.id.desc())
    if keyword:
        key = f"%{keyword.strip()}%"
        stmt = stmt.where(
            or_(
                AddressResource.category.ilike(key),
                AddressResource.contact_info.ilike(key),
                AddressResource.description.ilike(key),
                AddressResource.next_action.ilike(key),
            )
        )
    return db.execute(stmt).scalars().all()


@router.post("", response_model=AddressResourceOut, status_code=status.HTTP_201_CREATED)
def create_address_resource(
    payload: AddressResourceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = payload.model_dump()
    data["category"] = data["category"].strip()
    data["contact_info"] = data["contact_info"].strip()
    data["description"] = data["description"].strip()
    data["next_action"] = data["next_action"].strip()
    data["notes"] = data["notes"].strip()

    resource = AddressResource(**data)
    db.add(resource)
    write_operation_log(
        db,
        actor_id=current_user.id,
        action="ADDRESS_RESOURCE_CREATED",
        entity_type="ADDRESS_RESOURCE",
        entity_id=payload.category,
        detail=payload.contact_info,
    )
    db.commit()
    db.refresh(resource)
    return resource


@router.patch("/{resource_id}", response_model=AddressResourceOut)
def update_address_resource(
    resource_id: int,
    payload: AddressResourceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    resource = db.execute(
        select(AddressResource).where(AddressResource.id == resource_id)
    ).scalar_one_or_none()
    if resource is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Address resource not found")

    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

    for key, value in update_data.items():
        if value is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Field `{key}` cannot be null",
            )
        if isinstance(value, str):
            value = value.strip()
        setattr(resource, key, value)
    resource.updated_at = datetime.utcnow()
    write_operation_log(
        db,
        actor_id=current_user.id,
        action="ADDRESS_RESOURCE_UPDATED",
        entity_type="ADDRESS_RESOURCE",
        entity_id=resource.id,
        detail=resource.category,
    )
    db.commit()
    db.refresh(resource)
    return resource
