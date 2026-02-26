from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class AddressResourceCreate(BaseModel):
    category: str = Field(default="", max_length=120)
    contact_info: str = Field(default="", max_length=255)
    description: str = ""
    next_action: str = Field(default="", max_length=255)
    notes: str = ""


class AddressResourceUpdate(BaseModel):
    category: Optional[str] = None
    contact_info: Optional[str] = None
    description: Optional[str] = None
    next_action: Optional[str] = None
    notes: Optional[str] = None


class AddressResourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category: str
    contact_info: str
    description: str
    next_action: str
    notes: str
    created_at: datetime
    updated_at: datetime
