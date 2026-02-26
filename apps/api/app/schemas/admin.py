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


class OperationLogOut(BaseModel):
    id: int
    actor_id: Optional[int]
    actor_username: str
    action: str
    entity_type: str
    entity_id: str
    detail: str
    created_at: datetime
