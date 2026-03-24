from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class BillingRecordCreate(BaseModel):
    serial_no: Optional[int] = None
    customer_id: int = Field(gt=0)
    customer_name: str = ""
    charge_category: str = "代账"
    charge_mode: Literal["PERIODIC", "ONE_TIME"] = "PERIODIC"
    amount_basis: Literal["MONTHLY", "YEARLY", "ONE_TIME", "PERIOD_TOTAL"] = "MONTHLY"
    summary: str = ""
    total_fee: float = 0
    monthly_fee: float = 0
    billing_cycle_text: str = ""
    period_start_month: str = ""
    period_end_month: str = ""
    collection_start_date: str = ""
    due_month: str = ""
    payment_method: str = ""
    status: Literal["CLEARED", "FULL_ARREARS", "PARTIAL"] = "PARTIAL"
    received_amount: float = 0
    outstanding_amount: Optional[float] = None
    note: str = ""
    extra_note: str = ""
    color_tag: str = ""


class BillingRecordBatchCreate(BaseModel):
    records: list[BillingRecordCreate] = Field(min_length=1)


class BillingRecordUpdate(BaseModel):
    serial_no: Optional[int] = None
    customer_id: Optional[int] = None
    customer_name: Optional[str] = None
    charge_category: Optional[str] = None
    charge_mode: Optional[Literal["PERIODIC", "ONE_TIME"]] = None
    amount_basis: Optional[Literal["MONTHLY", "YEARLY", "ONE_TIME", "PERIOD_TOTAL"]] = None
    summary: Optional[str] = None
    total_fee: Optional[float] = None
    monthly_fee: Optional[float] = None
    billing_cycle_text: Optional[str] = None
    period_start_month: Optional[str] = None
    period_end_month: Optional[str] = None
    collection_start_date: Optional[str] = None
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
    charge_category: str
    charge_mode: str
    amount_basis: str
    summary: str
    customer_contact_name: str
    accountant_username: str
    total_fee: float
    monthly_fee: float
    billing_cycle_text: str
    period_start_month: str
    period_end_month: str
    collection_start_date: str
    due_month: str
    payment_method: str
    status: str
    received_amount: float
    outstanding_amount: float
    receivable_period_text: str
    latest_payment_at: Optional[date]
    latest_payment_amount: float
    latest_receipt_account: str
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
    receipt_account: str = ""
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
    actor_username: str
    payment_id: Optional[int]
    amount: float
    payment_nature: str
    receipt_account: str
    is_prepay: bool
    is_settlement: bool
    content: str
    next_followup_at: Optional[date]
    note: str
    created_at: datetime


class BillingAssignmentCreate(BaseModel):
    assignee_user_id: int = Field(gt=0)
    assignment_role: Literal["REGISTRATION", "DELIVERY", "OTHER"] = "DELIVERY"
    note: str = ""


class BillingAssignmentUpdate(BaseModel):
    assignment_role: Optional[Literal["REGISTRATION", "DELIVERY", "OTHER"]] = None
    is_active: Optional[bool] = None
    note: Optional[str] = None


class BillingAssignmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    billing_record_id: int
    assignee_user_id: int
    assignee_username: str
    assignee_role: str
    assignment_role: str
    is_active: bool
    note: str
    created_by_user_id: Optional[int]
    created_at: datetime
    updated_at: datetime


class BillingExecutionLogCreate(BaseModel):
    occurred_at: date
    progress_type: Literal["UPDATE", "MILESTONE", "BLOCKER", "DONE"] = "UPDATE"
    content: str
    next_action: str = ""
    due_date: Optional[date] = None
    note: str = ""


class BillingExecutionLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    billing_record_id: int
    occurred_at: date
    actor_id: int
    actor_username: str
    progress_type: str
    content: str
    next_action: str
    due_date: Optional[date]
    note: str
    created_at: datetime


class BillingPaymentSuggestRequest(BaseModel):
    customer_id: int = Field(gt=0)
    amount: float = Field(gt=0)
    strategy: Literal["DUE_DATE_ASC", "SERIAL_ASC", "AMOUNT_DESC"] = "DUE_DATE_ASC"


class BillingPaymentSuggestedAllocationOut(BaseModel):
    billing_record_id: int
    serial_no: int
    summary: str
    due_month: str
    outstanding_amount: float
    suggested_amount: float


class BillingPaymentSuggestOut(BaseModel):
    customer_id: int
    amount: float
    strategy: str
    outstanding_total: float
    suggested_total: float
    remaining_amount: float
    allocations: list[BillingPaymentSuggestedAllocationOut]


class BillingPaymentAllocationInput(BaseModel):
    billing_record_id: int = Field(gt=0)
    allocated_amount: float = Field(gt=0)


class BillingPaymentCreate(BaseModel):
    customer_id: int = Field(gt=0)
    occurred_at: date
    amount: float = Field(gt=0)
    strategy: Literal["DUE_DATE_ASC", "SERIAL_ASC", "AMOUNT_DESC"] = "DUE_DATE_ASC"
    receipt_account: str = ""
    note: str = ""
    allocations: list[BillingPaymentAllocationInput] = Field(min_length=1)


class BillingPaymentAllocationOut(BaseModel):
    id: int
    billing_record_id: int
    allocated_amount: float


class BillingPaymentOut(BaseModel):
    id: int
    customer_id: int
    occurred_at: date
    amount: float
    strategy: str
    receipt_account: str
    note: str
    created_by_user_id: int
    created_at: datetime
    allocations: list[BillingPaymentAllocationOut]


class BillingRenewRequest(BaseModel):
    note: Optional[str] = None
    extra_note: Optional[str] = None
    charge_category: Optional[str] = None
    charge_mode: Optional[Literal["PERIODIC", "ONE_TIME"]] = None
    amount_basis: Optional[Literal["MONTHLY", "YEARLY", "ONE_TIME", "PERIOD_TOTAL"]] = None
    summary: Optional[str] = None
    total_fee: Optional[float] = None
    monthly_fee: Optional[float] = None
    billing_cycle_text: Optional[str] = None
    period_start_month: Optional[str] = None
    period_end_month: Optional[str] = None
    collection_start_date: Optional[str] = None
    due_month: Optional[str] = None
    payment_method: Optional[str] = None
    status: Optional[Literal["CLEARED", "FULL_ARREARS", "PARTIAL"]] = None
    received_amount: Optional[float] = None
    color_tag: Optional[str] = None


class BillingTerminateRequest(BaseModel):
    terminated_at: date
    reduced_fee: float = Field(ge=0)
    reason: str = ""


class BillingLedgerEntryOut(BaseModel):
    occurred_at: date
    summary: str
    receivable_amount: float
    received_amount: float
    balance: float
    source_type: Literal["RECEIVABLE", "PAYMENT"]
    billing_record_id: Optional[int] = None
    receipt_account: str = ""


class BillingLedgerMonthlySummaryOut(BaseModel):
    month: str
    receivable_total: float
    received_total: float
    net_change: float
    ending_balance: float


class BillingLedgerOut(BaseModel):
    customer_id: int
    customer_name: str
    date_from: Optional[date]
    date_to: Optional[date]
    receivable_total: float
    received_total: float
    balance: float
    monthly_summaries: list[BillingLedgerMonthlySummaryOut]
    entries: list[BillingLedgerEntryOut]


class BillingReceiptAccountSummaryOut(BaseModel):
    receipt_account: str
    payment_count: int
    total_received: float
    last_received_at: Optional[date]


class BillingReceiptAccountEntryOut(BaseModel):
    occurred_at: date
    receipt_account: str
    customer_name: str
    summary: str
    received_amount: float
    cumulative_received: float
    actor_username: str
    payment_id: Optional[int] = None
    billing_record_id: Optional[int] = None


class BillingReceiptAccountLedgerOut(BaseModel):
    receipt_account: Optional[str]
    date_from: Optional[date]
    date_to: Optional[date]
    total_received: float
    payment_count: int
    account_summaries: list[BillingReceiptAccountSummaryOut]
    entries: list[BillingReceiptAccountEntryOut]
