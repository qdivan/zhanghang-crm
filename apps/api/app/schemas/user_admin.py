from typing import Literal, Optional

from pydantic import BaseModel, Field

UserRoleLiteral = Literal["OWNER", "ADMIN", "MANAGER", "ACCOUNTANT", "EXTERNAL_LEAD"]


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=6, max_length=128)
    role: UserRoleLiteral = "ACCOUNTANT"
    manager_user_id: Optional[int] = None
    display_name: str = Field(default="", max_length=255)
    phone: str = Field(default="", max_length=32)
    lead_name_prefix: str = Field(default="", max_length=64)
    is_active: bool = True


class UserUpdate(BaseModel):
    username: Optional[str] = Field(default=None, min_length=3, max_length=64)
    password: Optional[str] = Field(default=None, min_length=6, max_length=128)
    role: Optional[UserRoleLiteral] = None
    manager_user_id: Optional[int] = None
    display_name: Optional[str] = Field(default=None, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=32)
    lead_name_prefix: Optional[str] = Field(default=None, max_length=64)
    is_active: Optional[bool] = None
