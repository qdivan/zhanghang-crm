from typing import Literal, Optional

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=6, max_length=128)
    role: Literal["OWNER", "ADMIN", "ACCOUNTANT"] = "ACCOUNTANT"
    is_active: bool = True


class UserUpdate(BaseModel):
    username: Optional[str] = Field(default=None, min_length=3, max_length=64)
    password: Optional[str] = Field(default=None, min_length=6, max_length=128)
    role: Optional[Literal["OWNER", "ADMIN", "ACCOUNTANT"]] = None
    is_active: Optional[bool] = None
