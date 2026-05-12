from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class SoftDeleteMixin:
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    deleted_by_user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)


def _normalize_month_text(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""
    if len(raw) >= 7:
        return raw[:7]
    return raw


def _shift_month_text(month_text: str, delta: int) -> str:
    normalized = _normalize_month_text(month_text)
    if not normalized:
        return ""
    year, month = normalized.split("-")
    year_num = int(year)
    month_num = int(month)
    total = year_num * 12 + (month_num - 1) + delta
    shifted_year = total // 12
    shifted_month = total % 12 + 1
    return f"{shifted_year:04d}-{shifted_month:02d}"


def _format_month_text(month_text: str) -> str:
    normalized = _normalize_month_text(month_text)
    if not normalized:
        return ""
    year, month = normalized.split("-")
    return f"{year[2:4]}.{int(month)}"


class User(SoftDeleteMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    auth_source: Mapped[str] = mapped_column(String(20), default="LOCAL")
    ldap_dn: Mapped[str] = mapped_column(String(255), default="")
    email: Mapped[str] = mapped_column(String(255), default="", index=True)
    display_name: Mapped[str] = mapped_column(String(255), default="")
    phone: Mapped[str] = mapped_column(String(32), default="", index=True)
    lead_name_prefix: Mapped[str] = mapped_column(String(64), default="")
    external_managed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    role: Mapped[str] = mapped_column(String(20), default="ACCOUNTANT")
    manager_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    leads: Mapped[list["Lead"]] = relationship(back_populates="owner")
    assigned_customers: Mapped[list["Customer"]] = relationship(
        back_populates="accountant",
        foreign_keys="Customer.assigned_accountant_id",
    )
    responsible_customers: Mapped[list["Customer"]] = relationship(
        back_populates="responsible_user",
        foreign_keys="Customer.responsible_user_id",
    )
    customer_timeline_events: Mapped[list["CustomerTimelineEvent"]] = relationship(back_populates="actor")
    billing_activities: Mapped[list["BillingActivity"]] = relationship(back_populates="actor")
    billing_execution_logs: Mapped[list["BillingExecutionLog"]] = relationship(back_populates="actor")
    billing_payments: Mapped[list["BillingPayment"]] = relationship(back_populates="creator")
    identities: Mapped[list["UserIdentity"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    manager: Mapped[Optional["User"]] = relationship(
        remote_side=lambda: [User.id],
        foreign_keys=[manager_user_id],
        back_populates="direct_reports",
    )
    direct_reports: Mapped[list["User"]] = relationship(
        back_populates="manager",
        foreign_keys=[manager_user_id],
    )

    @property
    def manager_username(self) -> str:
        if self.manager is None:
            return ""
        return self.manager.username

    @property
    def sso_bound(self) -> bool:
        return len(self.identities) > 0


class UserIdentity(Base):
    __tablename__ = "user_identities"
    __table_args__ = (
        UniqueConstraint("provider", "issuer", "subject", name="uq_user_identities_provider_subject"),
        UniqueConstraint("user_id", "provider", name="uq_user_identities_user_provider"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    provider: Mapped[str] = mapped_column(String(32), default="keycloak", index=True)
    issuer: Mapped[str] = mapped_column(String(255), default="", index=True)
    subject: Mapped[str] = mapped_column(String(255), default="", index=True)
    preferred_username: Mapped[str] = mapped_column(String(255), default="")
    email: Mapped[str] = mapped_column(String(255), default="")
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    display_name: Mapped[str] = mapped_column(String(255), default="")
    raw_claims_json: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship(back_populates="identities")


class SsoBindingConflict(Base):
    __tablename__ = "sso_binding_conflicts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    provider: Mapped[str] = mapped_column(String(32), default="keycloak", index=True)
    issuer: Mapped[str] = mapped_column(String(255), default="", index=True)
    subject: Mapped[str] = mapped_column(String(255), default="", index=True)
    preferred_username: Mapped[str] = mapped_column(String(255), default="")
    email: Mapped[str] = mapped_column(String(255), default="")
    display_name: Mapped[str] = mapped_column(String(255), default="")
    raw_claims_json: Mapped[str] = mapped_column(Text, default="")
    reason: Mapped[str] = mapped_column(String(255), default="")
    status: Mapped[str] = mapped_column(String(32), default="PENDING", index=True)
    candidate_user_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    resolved_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    resolved_user: Mapped[Optional["User"]] = relationship()


class SsoLoginTicket(Base):
    __tablename__ = "sso_login_tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ticket: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    provider: Mapped[str] = mapped_column(String(32), default="keycloak", index=True)
    purpose: Mapped[str] = mapped_column(String(32), default="STATE", index=True)
    status: Mapped[str] = mapped_column(String(32), default="PENDING", index=True)
    nonce: Mapped[str] = mapped_column(String(255), default="")
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    conflict_id: Mapped[Optional[int]] = mapped_column(ForeignKey("sso_binding_conflicts.id"), nullable=True, index=True)
    error_code: Mapped[str] = mapped_column(String(64), default="")
    error_message: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    consumed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    user: Mapped[Optional["User"]] = relationship()
    conflict: Mapped[Optional["SsoBindingConflict"]] = relationship()
class Lead(SoftDeleteMixin, Base):
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
        if self.customer is None or self.customer.is_deleted:
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
    creator: Mapped[Optional["User"]] = relationship()

    @property
    def created_by_username(self) -> str:
        if self.creator is None:
            return ""
        return self.creator.username


class Customer(SoftDeleteMixin, Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    contact_name: Mapped[str] = mapped_column(String(100))
    phone: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    responsible_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    assigned_accountant_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    customer_code_seq: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    customer_code_suffix: Mapped[str] = mapped_column(String(8), default="")
    customer_code: Mapped[str] = mapped_column(String(32), default="", index=True)
    source_customer_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    source_lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id"), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    responsible_user: Mapped[Optional["User"]] = relationship(
        back_populates="responsible_customers",
        foreign_keys=[responsible_user_id],
    )
    accountant: Mapped[Optional["User"]] = relationship(
        back_populates="assigned_customers",
        foreign_keys=[assigned_accountant_id],
    )
    source_lead: Mapped["Lead"] = relationship(back_populates="customer")
    billing_records: Mapped[list["BillingRecord"]] = relationship(back_populates="customer")
    timeline_events: Mapped[list["CustomerTimelineEvent"]] = relationship(
        back_populates="customer",
        cascade="all, delete-orphan",
    )

    @property
    def responsible_username(self) -> str:
        if self.responsible_user is None:
            return ""
        return self.responsible_user.username

    @property
    def accountant_username(self) -> str:
        if self.accountant is None:
            return ""
        return self.accountant.username


class CustomerTimelineEvent(Base):
    __tablename__ = "customer_timeline_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    occurred_at: Mapped[date] = mapped_column(Date, default=date.today, index=True)
    event_type: Mapped[str] = mapped_column(String(32), default="COMMUNICATION", index=True)
    status: Mapped[str] = mapped_column(String(16), default="NOTE", index=True)
    reminder_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    completed_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    result: Mapped[str] = mapped_column(Text, default="")
    template_key: Mapped[str] = mapped_column(String(32), default="", index=True)
    content: Mapped[str] = mapped_column(Text, default="")
    note: Mapped[str] = mapped_column(Text, default="")
    amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    customer: Mapped["Customer"] = relationship(back_populates="timeline_events")
    actor: Mapped[Optional["User"]] = relationship(back_populates="customer_timeline_events")

    @property
    def actor_username(self) -> str:
        if self.actor is None:
            return ""
        return self.actor.username


class AddressResource(SoftDeleteMixin, Base):
    __tablename__ = "address_resources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    category: Mapped[str] = mapped_column(String(120), default="")
    contact_info: Mapped[str] = mapped_column(String(255), default="")
    served_companies: Mapped[str] = mapped_column(Text, default="")
    description: Mapped[str] = mapped_column(Text, default="")
    next_action: Mapped[str] = mapped_column(String(255), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
    company_items: Mapped[list["AddressResourceCompany"]] = relationship(
        back_populates="address_resource",
        cascade="all, delete-orphan",
    )


class AddressResourceCompany(SoftDeleteMixin, Base):
    __tablename__ = "address_resource_companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    address_resource_id: Mapped[int] = mapped_column(ForeignKey("address_resources.id"), index=True)
    customer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("customers.id"), nullable=True, index=True)
    company_name: Mapped[str] = mapped_column(String(200), default="", index=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    address_resource: Mapped["AddressResource"] = relationship(back_populates="company_items")
    customer: Mapped[Optional["Customer"]] = relationship()

    @property
    def customer_name(self) -> str:
        if self.customer is None:
            return ""
        return self.customer.name or ""


class CommonLibraryItem(SoftDeleteMixin, Base):
    __tablename__ = "common_library_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    module_type: Mapped[str] = mapped_column(String(32), default="TEMPLATE", index=True)
    visibility: Mapped[str] = mapped_column(String(16), default="INTERNAL", index=True)
    category: Mapped[str] = mapped_column(String(120), default="")
    title: Mapped[str] = mapped_column(String(255), default="")
    content: Mapped[str] = mapped_column(Text, default="")
    phone: Mapped[str] = mapped_column(String(64), default="")
    address: Mapped[str] = mapped_column(String(255), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class BillingRecord(SoftDeleteMixin, Base):
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
        if self.customer is None:
            return ""
        return self.customer.accountant_username or self.customer.responsible_username

    @property
    def customer_contact_name(self) -> str:
        if self.customer is None:
            return ""
        return self.customer.contact_name or ""

    @property
    def receivable_period_text(self) -> str:
        if self.charge_mode == "ONE_TIME":
            return self.collection_start_date or self.due_month or "-"
        start_month = _normalize_month_text(self.period_start_month or "")
        end_month = _normalize_month_text(self.period_end_month or "")
        if not start_month and self.collection_start_date:
            start_month = self.collection_start_date[:7]
        if not end_month and self.due_month:
            end_month = self.due_month[:7]
        if end_month and not start_month:
            start_month = _shift_month_text(end_month, -11)
        if start_month and not end_month:
            end_month = _shift_month_text(start_month, 11)
        if start_month and end_month:
            return f"{_format_month_text(start_month)}-{_format_month_text(end_month)}"
        start = (self.collection_start_date or "").strip()
        end = (self.due_month or "").strip()
        if start and end:
            return f"{start} ~ {end}"
        return start or end or "-"

    @property
    def latest_payment_at(self) -> Optional[date]:
        payment_rows = [
            item
            for item in self.activities
            if item.activity_type == "PAYMENT" and float(item.amount or 0) > 0
        ]
        if not payment_rows:
            return None
        latest = max(payment_rows, key=lambda item: (item.occurred_at, item.id))
        return latest.occurred_at

    @property
    def latest_payment_amount(self) -> float:
        payment_rows = [
            item
            for item in self.activities
            if item.activity_type == "PAYMENT" and float(item.amount or 0) > 0
        ]
        if not payment_rows:
            return 0.0
        latest = max(payment_rows, key=lambda item: (item.occurred_at, item.id))
        return float(latest.amount or 0)

    @property
    def latest_receipt_account(self) -> str:
        payment_rows = [
            item
            for item in self.activities
            if item.activity_type == "PAYMENT" and float(item.amount or 0) > 0
        ]
        if not payment_rows:
            return ""
        latest = max(payment_rows, key=lambda item: (item.occurred_at, item.id))
        return (latest.receipt_account or "").strip() or "未指定"


class BillingActivity(Base):
    __tablename__ = "billing_activities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    billing_record_id: Mapped[int] = mapped_column(ForeignKey("billing_records.id"), index=True)
    payment_id: Mapped[Optional[int]] = mapped_column(ForeignKey("billing_payments.id"), nullable=True, index=True)
    activity_type: Mapped[str] = mapped_column(String(20), default="REMINDER", index=True)
    occurred_at: Mapped[date] = mapped_column(Date, default=date.today)
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    amount: Mapped[float] = mapped_column(Float, default=0)
    payment_nature: Mapped[str] = mapped_column(String(20), default="")
    receipt_account: Mapped[str] = mapped_column(String(64), default="")
    is_prepay: Mapped[bool] = mapped_column(Boolean, default=False)
    is_settlement: Mapped[bool] = mapped_column(Boolean, default=False)
    content: Mapped[str] = mapped_column(Text, default="")
    next_followup_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    billing_record: Mapped["BillingRecord"] = relationship(back_populates="activities")
    actor: Mapped["User"] = relationship(back_populates="billing_activities")

    @property
    def actor_username(self) -> str:
        if self.actor is None:
            return ""
        return self.actor.username


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


class BillingPayment(SoftDeleteMixin, Base):
    __tablename__ = "billing_payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    occurred_at: Mapped[date] = mapped_column(Date, default=date.today, index=True)
    amount: Mapped[float] = mapped_column(Float, default=0)
    strategy: Mapped[str] = mapped_column(String(32), default="DUE_DATE_ASC")
    receipt_account: Mapped[str] = mapped_column(String(64), default="")
    is_prepay: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    note: Mapped[str] = mapped_column(Text, default="")
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    customer: Mapped["Customer"] = relationship()
    creator: Mapped["User"] = relationship(back_populates="billing_payments")
    allocations: Mapped[list["BillingPaymentAllocation"]] = relationship(
        back_populates="payment",
        cascade="all, delete-orphan",
    )

    @property
    def payment_no(self) -> str:
        return f"SK{self.id:04d}"


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
    assignment_kind: Mapped[str] = mapped_column(String(16), default="CC", index=True)
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


class TodoItem(SoftDeleteMixin, Base):
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


class DataAccessGrant(SoftDeleteMixin, Base):
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
