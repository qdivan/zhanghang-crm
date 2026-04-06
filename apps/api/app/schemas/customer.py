from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.lead import LeadOut, LeadFollowupOut


class CustomerListOut(BaseModel):
    id: int
    name: str
    contact_name: str
    phone: str
    status: str
    assigned_accountant_id: int
    accountant_username: str
    source_customer_id: Optional[int]
    source_lead_id: int
    source_template_type: str
    source_grade: str
    source_country: str
    source_service_start_text: str
    source_area_display: str
    source_service_start_display: str
    source_company_nature: str
    source_service_mode: str
    source_contact_wechat: str
    source_other_contact: str
    source_main_business: str
    source_intro: str
    source_fee_standard: str
    source_first_billing_period: str
    source_last_followup_date: Optional[date]
    source_reminder_value: str
    created_at: datetime


class CustomerDetailOut(BaseModel):
    id: int
    name: str
    contact_name: str
    phone: str
    status: str
    assigned_accountant_id: int
    accountant_username: str
    source_customer_id: Optional[int]
    source_lead_id: int
    created_at: datetime
    lead: LeadOut
    followups: list[LeadFollowupOut]
    timeline: list["CustomerTimelineEntryOut"]


class CustomerTimelineEventCreate(BaseModel):
    occurred_at: date
    event_type: str = Field(default="COMMUNICATION", min_length=1, max_length=32)
    status: str = Field(default="NOTE", min_length=1, max_length=16)
    reminder_at: Optional[date] = None
    completed_at: Optional[date] = None
    content: str = ""
    note: str = ""
    result: str = ""
    amount: Optional[float] = None


class CustomerTimelineEventUpdate(BaseModel):
    occurred_at: Optional[date] = None
    event_type: Optional[str] = Field(default=None, min_length=1, max_length=32)
    status: Optional[str] = Field(default=None, min_length=1, max_length=16)
    reminder_at: Optional[date] = None
    completed_at: Optional[date] = None
    content: Optional[str] = None
    note: Optional[str] = None
    result: Optional[str] = None
    amount: Optional[float] = None


class CustomerTimelineEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    occurred_at: date
    event_type: str
    status: str
    reminder_at: Optional[date]
    completed_at: Optional[date]
    content: str
    note: str
    result: str
    amount: Optional[float]
    template_key: str
    actor_id: int
    actor_username: str
    created_at: datetime


class CustomerTimelineEntryOut(BaseModel):
    occurred_at: date
    source_type: str
    source_id: Optional[int] = None
    title: str
    content: str
    note: str = ""
    amount: Optional[float] = None
    status: str = ""
    reminder_at: Optional[date] = None
    completed_at: Optional[date] = None
    result: str = ""
    actor_username: str = ""
    extra: str = ""


class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    contact_name: Optional[str] = None
    phone: Optional[str] = None
    status: Optional[str] = None
    assigned_accountant_id: Optional[int] = None

    lead_grade: Optional[str] = None
    lead_contact_wechat: Optional[str] = None
    lead_fax: Optional[str] = None
    lead_other_contact: Optional[str] = None
    lead_region: Optional[str] = None
    lead_country: Optional[str] = None
    lead_service_start_text: Optional[str] = None
    lead_company_nature: Optional[str] = None
    lead_service_mode: Optional[str] = None
    lead_fee_standard: Optional[str] = None
    lead_first_billing_period: Optional[str] = None
    lead_reminder_value: Optional[str] = None
    lead_next_reminder_at: Optional[date] = None
    lead_source: Optional[str] = None
    lead_main_business: Optional[str] = None
    lead_intro: Optional[str] = None
    lead_notes: Optional[str] = None


CustomerDetailOut.model_rebuild()
