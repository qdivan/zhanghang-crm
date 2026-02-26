from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class BillingRecordCreate(BaseModel):
    serial_no: Optional[int] = None
    customer_id: int = Field(gt=0)
    customer_name: str = ""
    total_fee: float = 0
    monthly_fee: float = 0
    billing_cycle_text: str = ""
    due_month: str = ""
    payment_method: str = ""
    status: Literal["CLEARED", "FULL_ARREARS", "PARTIAL"] = "PARTIAL"
    received_amount: float = 0
    outstanding_amount: Optional[float] = None
    note: str = ""
    extra_note: str = ""
    color_tag: str = ""


class BillingRecordUpdate(BaseModel):
    serial_no: Optional[int] = None
    customer_id: Optional[int] = None
    customer_name: Optional[str] = None
    total_fee: Optional[float] = None
    monthly_fee: Optional[float] = None
    billing_cycle_text: Optional[str] = None
    due_month: Optional[str] = None
    payment_method: Optional[str] = None
    status: Optional[Literal["CLEARED", "FULL_ARREARS", "PARTIAL"]] = None
    received_amount: Optional[float] = None
    outstanding_amount: Optional[float] = None
    note: Optional[str] = None
    extra_note: Optional[str] = None
    color_tag: Optional[str] = None


class BillingRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    serial_no: int
    customer_id: Optional[int]
    customer_name: str
    accountant_username: str
    total_fee: float
    monthly_fee: float
    billing_cycle_text: str
    due_month: str
    payment_method: str
    status: str
    received_amount: float
    outstanding_amount: float
    note: str
    extra_note: str
    color_tag: str
    created_at: datetime
    updated_at: datetime


class BillingActivityCreate(BaseModel):
    activity_type: Literal["REMINDER", "PAYMENT"]
    occurred_at: date
    amount: float = 0
    payment_nature: Literal["", "MONTHLY", "YEARLY", "ONE_OFF"] = ""
    is_prepay: bool = False
    is_settlement: bool = False
    content: str = ""
    next_followup_at: Optional[date] = None
    note: str = ""


class BillingActivityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    billing_record_id: int
    activity_type: str
    occurred_at: date
    actor_id: int
    amount: float
    payment_nature: str
    is_prepay: bool
    is_settlement: bool
    content: str
    next_followup_at: Optional[date]
    note: str
    created_at: datetime
