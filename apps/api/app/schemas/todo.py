from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class TodoCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = ""
    priority: Literal["HIGH", "MEDIUM", "LOW"] = "MEDIUM"
    due_date: Optional[date] = None
    assignee_user_id: Optional[int] = Field(default=None, gt=0)
    is_in_today: bool = False


class TodoUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
    priority: Optional[Literal["HIGH", "MEDIUM", "LOW"]] = None
    due_date: Optional[date] = None
    status: Optional[Literal["OPEN", "DONE"]] = None
    is_in_today: Optional[bool] = None


class TodoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    priority: Literal["HIGH", "MEDIUM", "LOW"]
    due_date: Optional[date]
    my_day_date: Optional[date]
    is_in_today: bool
    status: Literal["OPEN", "DONE"]
    assignee_user_id: int
    assignee_username: str
    created_by_user_id: int
    created_by_username: str
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class TodoBulkUpdateResult(BaseModel):
    affected_count: int
