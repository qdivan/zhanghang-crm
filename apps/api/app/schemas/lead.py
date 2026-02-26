from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class LeadCreate(BaseModel):
    template_type: str = "FOLLOWUP"
    name: str = Field(min_length=2, max_length=200)
    grade: str = ""
    contact_name: str = Field(min_length=1, max_length=100)
    phone: str = Field(min_length=6, max_length=32)
    region: str = ""
    country: str = ""
    source: str = ""
    contact_wechat: str = ""
    fax: str = ""
    other_contact: str = ""
    contact_start_date: Optional[date] = None
    service_start_text: str = ""
    company_nature: str = ""
    service_mode: str = ""
    main_business: str = ""
    intro: str = ""
    fee_standard: str = ""
    first_billing_period: str = ""
    reserve_2: str = ""
    reserve_3: str = ""
    reserve_4: str = ""
    next_reminder_at: Optional[date] = None
    reminder_value: str = ""
    notes: str = ""
    owner_id: Optional[int] = None


class LeadUpdate(BaseModel):
    name: Optional[str] = None
    contact_name: Optional[str] = None
    phone: Optional[str] = None
    template_type: Optional[str] = None
    grade: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None
    contact_wechat: Optional[str] = None
    fax: Optional[str] = None
    other_contact: Optional[str] = None
    contact_start_date: Optional[date] = None
    service_start_text: Optional[str] = None
    company_nature: Optional[str] = None
    service_mode: Optional[str] = None
    main_business: Optional[str] = None
    intro: Optional[str] = None
    fee_standard: Optional[str] = None
    first_billing_period: Optional[str] = None
    reserve_2: Optional[str] = None
    reserve_3: Optional[str] = None
    reserve_4: Optional[str] = None
    status: Optional[str] = None
    source: Optional[str] = None
    next_reminder_at: Optional[date] = None
    reminder_value: Optional[str] = None
    notes: Optional[str] = None


class LeadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    template_type: str
    name: str
    grade: str
    contact_name: str
    phone: str
    region: str
    country: str
    source: str
    contact_wechat: str
    fax: str
    other_contact: str
    contact_start_date: Optional[date]
    service_start_text: str
    company_nature: str
    service_mode: str
    main_business: str
    intro: str
    fee_standard: str
    first_billing_period: str
    reserve_2: str
    reserve_3: str
    reserve_4: str
    customer_id: Optional[int]
    status: str
    next_reminder_at: Optional[date]
    last_followup_date: Optional[date]
    reminder_value: str
    last_feedback: str
    notes: str
    owner_id: int
    created_at: datetime
    updated_at: datetime


class LeadFollowupCreate(BaseModel):
    followup_at: date
    feedback: str
    next_reminder_at: Optional[date] = None
    notes: str = ""


class LeadFollowupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lead_id: int
    followup_at: date
    feedback: str
    next_reminder_at: Optional[date]
    notes: str
    created_by: int
    created_at: datetime


class ConvertLeadRequest(BaseModel):
    accountant_id: Optional[int] = None
    customer_name: Optional[str] = None
    customer_contact_name: Optional[str] = None
    customer_phone: Optional[str] = None


class CustomerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    contact_name: str
    phone: str
    status: str
    assigned_accountant_id: int
    source_lead_id: int
    created_at: datetime


class ConvertLeadResponse(BaseModel):
    lead: LeadOut
    customer: CustomerOut
