from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AddressResourceCreate(BaseModel):
    category: str = Field(default="", max_length=120)
    contact_info: str = Field(default="", max_length=255)
    served_companies: str = ""
    description: str = ""
    next_action: str = Field(default="", max_length=255)
    notes: str = ""

    @model_validator(mode="after")
    def validate_business_fields(self):
        if not any(
            [
                self.category.strip(),
                self.contact_info.strip(),
                self.served_companies.strip(),
                self.description.strip(),
            ]
        ):
            raise ValueError("分类、地址/联系人、已服务公司、资源说明不能同时为空")
        return self


class AddressResourceUpdate(BaseModel):
    category: Optional[str] = None
    contact_info: Optional[str] = None
    served_companies: Optional[str] = None
    description: Optional[str] = None
    next_action: Optional[str] = None
    notes: Optional[str] = None


class AddressResourceCompanyCreate(BaseModel):
    customer_id: Optional[int] = Field(default=None, gt=0)
    company_name: str = Field(default="", max_length=200)
    notes: str = ""


class AddressResourceCompanyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    address_resource_id: int
    customer_id: Optional[int]
    customer_name: str
    company_name: str
    notes: str
    created_at: datetime
    updated_at: datetime


class AddressResourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category: str
    contact_info: str
    served_companies: str
    served_company_count: int
    company_items: list[AddressResourceCompanyOut]
    description: str
    next_action: str
    notes: str
    created_at: datetime
    updated_at: datetime
