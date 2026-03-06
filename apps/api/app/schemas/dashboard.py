from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel


class DashboardSummaryOut(BaseModel):
    month: str
    lead_new_count: int
    lead_following_count: int
    customer_count: int
    billing_record_count: int
    outstanding_amount_total: float
    manual_open_todo_count: int
    system_todo_count: int


class SystemTodoOut(BaseModel):
    id: str
    module: Literal["LEAD", "BILLING"]
    priority: Literal["HIGH", "MEDIUM", "LOW"]
    title: str
    description: str
    due_date: Optional[date]
    action_path: str
    action_label: str
    assignee_user_id: Optional[int]
    assignee_username: str
