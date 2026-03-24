from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    auth_source: str
    ldap_dn: str
    role: str
    manager_user_id: Optional[int] = None
    manager_username: str = ""
    is_active: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None
    granted_read_modules: list[str] = []
