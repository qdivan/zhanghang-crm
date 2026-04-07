from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import exists, or_, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models import AddressResource, AddressResourceCompany, Customer, User
from app.schemas.address_resource import (
    AddressResourceCompanyCreate,
    AddressResourceCompanyOut,
    AddressResourceCreate,
    AddressResourceOut,
    AddressResourceUpdate,
)
from app.services.audit import write_operation_log
from app.services.soft_delete import active_filter, mark_deleted

router = APIRouter(prefix="/address-resources", tags=["address-resources"])


def _split_company_names(raw_text: str) -> list[str]:
    tokens = (
        raw_text.replace("，", "、")
        .replace(",", "、")
        .replace("\n", "、")
        .split("、")
    )
    return [item.strip() for item in tokens if item and item.strip()]


def _build_resource_primary_name(resource: AddressResource) -> str:
    return (resource.category or "").strip() or (resource.contact_info or "").strip() or f"地址资源#{resource.id}"


def _sync_resource_served_companies_text(resource: AddressResource) -> None:
    names = [
        ((item.company_name or "").strip() or (item.customer_name or "").strip())
        for item in resource.company_items
        if not item.is_deleted
    ]
    resource.served_companies = "、".join([item for item in names if item])


def _serialize_company_item(item: AddressResourceCompany) -> AddressResourceCompanyOut:
    company_name = (item.company_name or "").strip() or item.customer_name
    return AddressResourceCompanyOut(
        id=item.id,
        address_resource_id=item.address_resource_id,
        customer_id=item.customer_id,
        customer_name=item.customer_name,
        company_name=company_name,
        notes=item.notes,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _serialize_resource(resource: AddressResource) -> AddressResourceOut:
    company_items = sorted(
        [item for item in resource.company_items if not item.is_deleted],
        key=lambda item: item.id,
    )
    preview_names = [
        ((item.company_name or "").strip() or (item.customer_name or "").strip())
        for item in company_items
    ]
    preview_text = "、".join([item for item in preview_names if item]) or (resource.served_companies or "").strip()
    return AddressResourceOut(
        id=resource.id,
        category=resource.category,
        contact_info=resource.contact_info,
        served_companies=preview_text,
        served_company_count=len(company_items),
        company_items=[_serialize_company_item(item) for item in company_items],
        description=resource.description,
        next_action=resource.next_action,
        notes=resource.notes,
        created_at=resource.created_at,
        updated_at=resource.updated_at,
    )


def _get_resource_or_404(db: Session, resource_id: int) -> AddressResource:
    resource = db.execute(
        select(AddressResource)
        .options(selectinload(AddressResource.company_items).selectinload(AddressResourceCompany.customer))
        .where(AddressResource.id == resource_id, active_filter(AddressResource))
    ).scalar_one_or_none()
    if resource is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="挂靠地址不存在")
    return resource


def _get_company_item_or_404(db: Session, resource_id: int, company_id: int) -> AddressResourceCompany:
    item = db.execute(
        select(AddressResourceCompany)
        .options(selectinload(AddressResourceCompany.customer))
        .where(
            AddressResourceCompany.address_resource_id == resource_id,
            AddressResourceCompany.id == company_id,
            active_filter(AddressResourceCompany),
        )
    ).scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="已服务公司不存在")
    return item


@router.get("", response_model=list[AddressResourceOut])
def list_address_resources(
    keyword: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    del current_user
    stmt = select(AddressResource).options(
        selectinload(AddressResource.company_items).selectinload(AddressResourceCompany.customer)
    ).where(active_filter(AddressResource)).order_by(AddressResource.id.desc())
    if keyword:
        key = f"%{keyword.strip()}%"
        stmt = stmt.where(
            or_(
                AddressResource.category.ilike(key),
                AddressResource.contact_info.ilike(key),
                AddressResource.description.ilike(key),
                AddressResource.next_action.ilike(key),
                AddressResource.notes.ilike(key),
                AddressResource.served_companies.ilike(key),
                exists(
                    select(AddressResourceCompany.id).where(
                        AddressResourceCompany.address_resource_id == AddressResource.id,
                        active_filter(AddressResourceCompany),
                        AddressResourceCompany.company_name.ilike(key),
                    )
                ),
            )
        )
    rows = db.execute(stmt).scalars().all()
    return [_serialize_resource(item) for item in rows]


@router.post("", response_model=AddressResourceOut, status_code=status.HTTP_201_CREATED)
def create_address_resource(
    payload: AddressResourceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = payload.model_dump()
    for key, value in data.items():
        if isinstance(value, str):
            data[key] = value.strip()

    resource = AddressResource(**data)
    db.add(resource)
    db.flush()

    if data.get("served_companies"):
        for company_name in _split_company_names(data["served_companies"]):
            db.add(
                AddressResourceCompany(
                    address_resource_id=resource.id,
                    company_name=company_name,
                )
            )
        db.flush()
        resource = _get_resource_or_404(db, resource.id)
        _sync_resource_served_companies_text(resource)

    write_operation_log(
        db,
        actor_id=current_user.id,
        action="ADDRESS_RESOURCE_CREATED",
        entity_type="ADDRESS_RESOURCE",
        entity_id=payload.category or resource.id,
        detail=payload.contact_info or payload.served_companies,
    )
    db.commit()
    resource = _get_resource_or_404(db, resource.id)
    return _serialize_resource(resource)


@router.patch("/{resource_id}", response_model=AddressResourceOut)
def update_address_resource(
    resource_id: int,
    payload: AddressResourceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    resource = _get_resource_or_404(db, resource_id)

    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="没有可更新的字段")

    served_companies_override = None
    for key, value in update_data.items():
        if value is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"字段 {key} 不能为空")
        if isinstance(value, str):
            value = value.strip()
        if key == "served_companies":
            served_companies_override = value
            continue
        setattr(resource, key, value)

    if served_companies_override is not None:
        existing_items = list(resource.company_items)
        for item in existing_items:
            if not item.is_deleted:
                mark_deleted(item, current_user.id)
        db.flush()
        for company_name in _split_company_names(served_companies_override):
            db.add(
                AddressResourceCompany(
                    address_resource_id=resource.id,
                    company_name=company_name,
                )
            )
        db.flush()
        resource = _get_resource_or_404(db, resource.id)
        _sync_resource_served_companies_text(resource)

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
    resource = _get_resource_or_404(db, resource.id)
    return _serialize_resource(resource)


@router.post(
    "/{resource_id}/companies",
    response_model=AddressResourceCompanyOut,
    status_code=status.HTTP_201_CREATED,
)
def create_address_resource_company(
    resource_id: int,
    payload: AddressResourceCompanyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    resource = _get_resource_or_404(db, resource_id)
    customer = None
    if payload.customer_id is not None:
        customer = db.execute(select(Customer).where(Customer.id == payload.customer_id, active_filter(Customer))).scalar_one_or_none()
        if customer is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Customer not found")

    company_name = (payload.company_name or "").strip() or (customer.name if customer is not None else "")
    if not company_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请填写公司名称或选择客户")

    item = AddressResourceCompany(
        address_resource_id=resource.id,
        customer_id=customer.id if customer is not None else None,
        company_name=company_name,
        notes=(payload.notes or "").strip(),
    )
    db.add(item)
    db.flush()
    resource = _get_resource_or_404(db, resource.id)
    _sync_resource_served_companies_text(resource)
    resource.updated_at = datetime.utcnow()
    write_operation_log(
        db,
        actor_id=current_user.id,
        action="ADDRESS_RESOURCE_COMPANY_CREATED",
        entity_type="ADDRESS_RESOURCE_COMPANY",
        entity_id=item.id,
        detail=f"resource_id={resource.id},company_name={company_name}",
    )
    db.commit()
    item = _get_company_item_or_404(db, resource.id, item.id)
    return _serialize_company_item(item)


@router.delete(
    "/{resource_id}/companies/{company_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles("OWNER", "ADMIN"))],
)
def delete_address_resource_company(
    resource_id: int,
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    resource = _get_resource_or_404(db, resource_id)
    item = _get_company_item_or_404(db, resource.id, company_id)
    expected_name = (item.company_name or "").strip() or item.customer_name
    mark_deleted(item, current_user.id)
    db.flush()
    resource = _get_resource_or_404(db, resource.id)
    _sync_resource_served_companies_text(resource)
    resource.updated_at = datetime.utcnow()
    write_operation_log(
        db,
        actor_id=current_user.id,
        action="ADDRESS_RESOURCE_COMPANY_DELETED",
        entity_type="ADDRESS_RESOURCE_COMPANY",
        entity_id=company_id,
        detail=expected_name,
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(
    "/{resource_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles("OWNER", "ADMIN"))],
)
def delete_address_resource(
    resource_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    resource = _get_resource_or_404(db, resource_id)
    expected_name = _build_resource_primary_name(resource)
    mark_deleted(resource, current_user.id)
    write_operation_log(
        db,
        actor_id=current_user.id,
        action="ADDRESS_RESOURCE_DELETED",
        entity_type="ADDRESS_RESOURCE",
        entity_id=resource_id,
        detail=expected_name,
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
