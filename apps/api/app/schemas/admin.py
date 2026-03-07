from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class LdapSettingsOut(BaseModel):
    id: int
    enabled: bool
    server_url: str
    bind_dn: str
    has_bind_password: bool
    base_dn: str
    user_base_dn: str
    user_filter: str
    username_attr: str
    display_name_attr: str
    default_role: str
    created_at: datetime
    updated_at: datetime


class LdapSettingsUpdate(BaseModel):
    enabled: Optional[bool] = None
    server_url: Optional[str] = None
    bind_dn: Optional[str] = None
    bind_password: Optional[str] = Field(default=None, max_length=255)
    base_dn: Optional[str] = None
    user_base_dn: Optional[str] = None
    user_filter: Optional[str] = None
    username_attr: Optional[str] = None
    display_name_attr: Optional[str] = None
    default_role: Optional[Literal["OWNER", "ADMIN", "ACCOUNTANT"]] = None


class LdapSyncResponse(BaseModel):
    total_found: int
    created_count: int
    updated_count: int
    skipped_count: int
    message: str = ""


class SecuritySettingsOut(BaseModel):
    id: int
    local_ip_lock_enabled: bool
    local_ip_lock_window_minutes: int
    local_ip_lock_max_attempts: int
    created_at: datetime
    updated_at: datetime


class SecuritySettingsUpdate(BaseModel):
    local_ip_lock_enabled: Optional[bool] = None
    local_ip_lock_window_minutes: Optional[int] = Field(default=None, ge=1, le=1440)
    local_ip_lock_max_attempts: Optional[int] = Field(default=None, ge=1, le=1000)


class OperationLogOut(BaseModel):
    id: int
    actor_id: Optional[int]
    actor_username: str
    action: str
    entity_type: str
    entity_id: str
    detail: str
    created_at: datetime


class DataAccessGrantCreate(BaseModel):
    grantee_user_id: int = Field(gt=0)
    module: Literal["CUSTOMER", "BILLING"]
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    reason: str = Field(default="", max_length=2000)
    is_active: bool = True


class DataAccessGrantUpdate(BaseModel):
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    reason: Optional[str] = Field(default=None, max_length=2000)
    is_active: Optional[bool] = None


class DataAccessGrantOut(BaseModel):
    id: int
    grantee_user_id: int
    grantee_username: str
    module: Literal["CUSTOMER", "BILLING"]
    is_active: bool
    is_effective: bool
    starts_at: Optional[datetime]
    ends_at: Optional[datetime]
    reason: str
    granted_by_user_id: Optional[int]
    granted_by_username: str
    created_at: datetime
    updated_at: datetime
