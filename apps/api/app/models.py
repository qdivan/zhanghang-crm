from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    auth_source: Mapped[str] = mapped_column(String(20), default="LOCAL")
    ldap_dn: Mapped[str] = mapped_column(String(255), default="")
    role: Mapped[str] = mapped_column(String(20), default="ACCOUNTANT")
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    leads: Mapped[list["Lead"]] = relationship(back_populates="owner")
    assigned_customers: Mapped[list["Customer"]] = relationship(back_populates="accountant")
    billing_activities: Mapped[list["BillingActivity"]] = relationship(back_populates="actor")
    billing_execution_logs: Mapped[list["BillingExecutionLog"]] = relationship(back_populates="actor")
    billing_payments: Mapped[list["BillingPayment"]] = relationship(back_populates="creator")


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    template_type: Mapped[str] = mapped_column(String(20), default="FOLLOWUP")
    name: Mapped[str] = mapped_column(String(200), index=True)
    grade: Mapped[str] = mapped_column(String(16), default="")
    contact_name: Mapped[str] = mapped_column(String(100))
    phone: Mapped[str] = mapped_column(String(32), index=True)
    region: Mapped[str] = mapped_column(String(120), default="")
    country: Mapped[str] = mapped_column(String(120), default="")
    source: Mapped[str] = mapped_column(String(100), default="")
    contact_wechat: Mapped[str] = mapped_column(String(120), default="")
    fax: Mapped[str] = mapped_column(String(64), default="")
    other_contact: Mapped[str] = mapped_column(Text, default="")
    contact_start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    service_start_text: Mapped[str] = mapped_column(String(64), default="")
    company_nature: Mapped[str] = mapped_column(String(120), default="")
    service_mode: Mapped[str] = mapped_column(String(120), default="")
    main_business: Mapped[str] = mapped_column(Text, default="")
    intro: Mapped[str] = mapped_column(Text, default="")
    fee_standard: Mapped[str] = mapped_column(String(120), default="")
    first_billing_period: Mapped[str] = mapped_column(String(120), default="")
    reserve_2: Mapped[str] = mapped_column(String(120), default="")
    reserve_3: Mapped[str] = mapped_column(String(120), default="")
    reserve_4: Mapped[str] = mapped_column(String(120), default="")
    status: Mapped[str] = mapped_column(String(20), default="NEW", index=True)
    next_reminder_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    last_followup_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    reminder_value: Mapped[str] = mapped_column(String(64), default="")
    last_feedback: Mapped[str] = mapped_column(Text, default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    related_customer_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    owner: Mapped["User"] = relationship(back_populates="leads")
    followups: Mapped[list["LeadFollowup"]] = relationship(
        back_populates="lead",
        cascade="all, delete-orphan",
    )
    customer: Mapped[Optional["Customer"]] = relationship(back_populates="source_lead")

    @property
    def customer_id(self) -> Optional[int]:
        if self.customer is None:
            return self.related_customer_id
        return self.customer.id


class LeadFollowup(Base):
    __tablename__ = "lead_followups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id"), index=True)
    followup_at: Mapped[date] = mapped_column(Date, default=date.today)
    feedback: Mapped[str] = mapped_column(Text)
    next_reminder_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    lead: Mapped["Lead"] = relationship(back_populates="followups")


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    contact_name: Mapped[str] = mapped_column(String(100))
    phone: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    assigned_accountant_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    source_lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id"), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    accountant: Mapped["User"] = relationship(back_populates="assigned_customers")
    source_lead: Mapped["Lead"] = relationship(back_populates="customer")
    billing_records: Mapped[list["BillingRecord"]] = relationship(back_populates="customer")


class AddressResource(Base):
    __tablename__ = "address_resources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    category: Mapped[str] = mapped_column(String(120), default="")
    contact_info: Mapped[str] = mapped_column(String(255), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    next_action: Mapped[str] = mapped_column(String(255), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class BillingRecord(Base):
    __tablename__ = "billing_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    serial_no: Mapped[int] = mapped_column(Integer, default=0, index=True)
    customer_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("customers.id"),
        nullable=True,
        index=True,
    )
    customer_name: Mapped[str] = mapped_column(String(200), index=True)
    charge_category: Mapped[str] = mapped_column(String(64), default="代账", index=True)
    charge_mode: Mapped[str] = mapped_column(String(20), default="PERIODIC", index=True)
    amount_basis: Mapped[str] = mapped_column(String(20), default="MONTHLY")
    summary: Mapped[str] = mapped_column(String(255), default="")
    total_fee: Mapped[float] = mapped_column(Float, default=0)
    monthly_fee: Mapped[float] = mapped_column(Float, default=0)
    billing_cycle_text: Mapped[str] = mapped_column(String(255), default="")
    period_start_month: Mapped[str] = mapped_column(String(7), default="")
    period_end_month: Mapped[str] = mapped_column(String(7), default="")
    collection_start_date: Mapped[str] = mapped_column(String(32), default="")
    due_month: Mapped[str] = mapped_column(String(32), default="")
    payment_method: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(32), default="PARTIAL", index=True)
    received_amount: Mapped[float] = mapped_column(Float, default=0)
    outstanding_amount: Mapped[float] = mapped_column(Float, default=0)
    note: Mapped[str] = mapped_column(Text, default="")
    extra_note: Mapped[str] = mapped_column(Text, default="")
    color_tag: Mapped[str] = mapped_column(String(32), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
    activities: Mapped[list["BillingActivity"]] = relationship(
        back_populates="billing_record",
        cascade="all, delete-orphan",
    )
    execution_logs: Mapped[list["BillingExecutionLog"]] = relationship(
        back_populates="billing_record",
        cascade="all, delete-orphan",
    )
    payment_allocations: Mapped[list["BillingPaymentAllocation"]] = relationship(
        back_populates="billing_record",
        cascade="all, delete-orphan",
    )
    assignments: Mapped[list["BillingAssignment"]] = relationship(
        back_populates="billing_record",
        cascade="all, delete-orphan",
    )
    customer: Mapped[Optional["Customer"]] = relationship(back_populates="billing_records")

    @property
    def accountant_username(self) -> str:
        if self.customer is None or self.customer.accountant is None:
            return ""
        return self.customer.accountant.username

    @property
    def customer_contact_name(self) -> str:
        if self.customer is None:
            return ""
        return self.customer.contact_name or ""


class BillingActivity(Base):
    __tablename__ = "billing_activities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    billing_record_id: Mapped[int] = mapped_column(ForeignKey("billing_records.id"), index=True)
    activity_type: Mapped[str] = mapped_column(String(20), default="REMINDER", index=True)
    occurred_at: Mapped[date] = mapped_column(Date, default=date.today)
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    amount: Mapped[float] = mapped_column(Float, default=0)
    payment_nature: Mapped[str] = mapped_column(String(20), default="")
    is_prepay: Mapped[bool] = mapped_column(Boolean, default=False)
    is_settlement: Mapped[bool] = mapped_column(Boolean, default=False)
    content: Mapped[str] = mapped_column(Text, default="")
    next_followup_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    billing_record: Mapped["BillingRecord"] = relationship(back_populates="activities")
    actor: Mapped["User"] = relationship(back_populates="billing_activities")


class BillingExecutionLog(Base):
    __tablename__ = "billing_execution_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    billing_record_id: Mapped[int] = mapped_column(ForeignKey("billing_records.id"), index=True)
    occurred_at: Mapped[date] = mapped_column(Date, default=date.today)
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    progress_type: Mapped[str] = mapped_column(String(20), default="UPDATE", index=True)
    content: Mapped[str] = mapped_column(Text, default="")
    next_action: Mapped[str] = mapped_column(Text, default="")
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    billing_record: Mapped["BillingRecord"] = relationship(back_populates="execution_logs")
    actor: Mapped["User"] = relationship(back_populates="billing_execution_logs")

    @property
    def actor_username(self) -> str:
        if self.actor is None:
            return ""
        return self.actor.username


class BillingPayment(Base):
    __tablename__ = "billing_payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    occurred_at: Mapped[date] = mapped_column(Date, default=date.today, index=True)
    amount: Mapped[float] = mapped_column(Float, default=0)
    strategy: Mapped[str] = mapped_column(String(32), default="DUE_DATE_ASC")
    note: Mapped[str] = mapped_column(Text, default="")
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    customer: Mapped["Customer"] = relationship()
    creator: Mapped["User"] = relationship(back_populates="billing_payments")
    allocations: Mapped[list["BillingPaymentAllocation"]] = relationship(
        back_populates="payment",
        cascade="all, delete-orphan",
    )


class BillingPaymentAllocation(Base):
    __tablename__ = "billing_payment_allocations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    payment_id: Mapped[int] = mapped_column(ForeignKey("billing_payments.id"), index=True)
    billing_record_id: Mapped[int] = mapped_column(ForeignKey("billing_records.id"), index=True)
    allocated_amount: Mapped[float] = mapped_column(Float, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    payment: Mapped["BillingPayment"] = relationship(back_populates="allocations")
    billing_record: Mapped["BillingRecord"] = relationship(back_populates="payment_allocations")


class BillingAssignment(Base):
    __tablename__ = "billing_assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    billing_record_id: Mapped[int] = mapped_column(ForeignKey("billing_records.id"), index=True)
    assignee_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    assignment_role: Mapped[str] = mapped_column(String(32), default="DELIVERY")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    note: Mapped[str] = mapped_column(Text, default="")
    created_by_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    billing_record: Mapped["BillingRecord"] = relationship(back_populates="assignments")
    assignee: Mapped[Optional["User"]] = relationship(foreign_keys=[assignee_user_id])

    @property
    def assignee_username(self) -> str:
        if self.assignee is None:
            return ""
        return self.assignee.username

    @property
    def assignee_role(self) -> str:
        if self.assignee is None:
            return ""
        return self.assignee.role


class TodoItem(Base):
    __tablename__ = "todo_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    priority: Mapped[str] = mapped_column(String(20), default="MEDIUM", index=True)
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    my_day_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default="OPEN", index=True)
    assignee_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class DataAccessGrant(Base):
    __tablename__ = "data_access_grants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    grantee_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    module: Mapped[str] = mapped_column(String(20), index=True)  # CUSTOMER / BILLING
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    starts_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    ends_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    reason: Mapped[str] = mapped_column(Text, default="")
    granted_by_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class OperationLog(Base):
    __tablename__ = "operation_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    actor_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(64), index=True)
    entity_type: Mapped[str] = mapped_column(String(64), default="", index=True)
    entity_id: Mapped[str] = mapped_column(String(64), default="")
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class LdapSetting(Base):
    __tablename__ = "ldap_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    server_url: Mapped[str] = mapped_column(String(255), default="")
    bind_dn: Mapped[str] = mapped_column(String(255), default="")
    bind_password: Mapped[str] = mapped_column(String(255), default="")
    base_dn: Mapped[str] = mapped_column(String(255), default="")
    user_base_dn: Mapped[str] = mapped_column(String(255), default="")
    user_filter: Mapped[str] = mapped_column(String(255), default="(uid=*)")
    username_attr: Mapped[str] = mapped_column(String(64), default="uid")
    display_name_attr: Mapped[str] = mapped_column(String(64), default="cn")
    default_role: Mapped[str] = mapped_column(String(20), default="ACCOUNTANT")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class SecuritySetting(Base):
    __tablename__ = "security_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    local_ip_lock_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    local_ip_lock_window_minutes: Mapped[int] = mapped_column(Integer, default=5)
    local_ip_lock_max_attempts: Mapped[int] = mapped_column(Integer, default=20)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class LoginIpLock(Base):
    __tablename__ = "login_ip_locks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ip_address: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    first_failed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_failed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    blocked_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_username: Mapped[str] = mapped_column(String(64), default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
