from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

CommonLibraryModuleType = Literal[
    "TEMPLATE",
    "DIRECTORY",
    "EXTENSION_A",
    "EXTENSION_B",
    "EXTENSION_C",
]
CommonLibraryVisibility = Literal["INTERNAL", "PUBLIC"]


class CommonLibraryItemBase(BaseModel):
    module_type: CommonLibraryModuleType
    visibility: CommonLibraryVisibility = "INTERNAL"
    category: str = Field(default="", max_length=120)
    title: str = Field(default="", max_length=255)
    content: str = ""
    phone: str = Field(default="", max_length=64)
    address: str = Field(default="", max_length=255)
    notes: str = ""


class CommonLibraryItemCreate(CommonLibraryItemBase):
    @model_validator(mode="after")
    def validate_business_fields(self):
        if not any(
            [
                self.category.strip(),
                self.title.strip(),
                self.content.strip(),
                self.phone.strip(),
                self.address.strip(),
                self.notes.strip(),
            ]
        ):
            raise ValueError("分类、标题、内容、电话、地址、备注不能同时为空")
        return self


class CommonLibraryItemUpdate(BaseModel):
    visibility: Optional[CommonLibraryVisibility] = None
    category: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None


class CommonLibraryItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    module_type: CommonLibraryModuleType
    visibility: CommonLibraryVisibility
    category: str
    title: str
    content: str
    phone: str
    address: str
    notes: str
    created_at: datetime
    updated_at: datetime
