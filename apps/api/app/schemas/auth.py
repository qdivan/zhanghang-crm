from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Optional["UserOut"] = None


class AuthProviderEntry(BaseModel):
    enabled: bool
    label: str
    admin_only: bool = False


class AuthProvidersOut(BaseModel):
    local: AuthProviderEntry
    sso: AuthProviderEntry


class SsoExchangeRequest(BaseModel):
    ticket: str


class SsoExchangeResponse(BaseModel):
    status: str
    message: str = ""
    access_token: Optional[str] = None
    token_type: str = "bearer"
    user: Optional["UserOut"] = None
    conflict_id: Optional[int] = None
    provider_label: str = ""


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    auth_source: str
    ldap_dn: str
    email: str = ""
    display_name: str = ""
    phone: str = ""
    lead_name_prefix: str = ""
    external_managed: bool = False
    sso_bound: bool = False
    role: str
    manager_user_id: Optional[int] = None
    manager_username: str = ""
    is_active: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None
    granted_read_modules: list[str] = []


TokenResponse.model_rebuild()
