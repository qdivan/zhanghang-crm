import re

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from app.api.v1.router import router as v1_router
from app.core.config import settings
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.services.bootstrap import bootstrap_data
from app import models as app_models

MODEL_IMPORT_GUARD = app_models

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router, prefix="/api/v1")


def _ensure_schema_compatibility() -> None:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())

    def ensure_soft_delete_columns(table_name: str) -> None:
        if table_name not in table_names:
            return
        columns = {item["name"] for item in inspector.get_columns(table_name)}
        with engine.begin() as conn:
            if "is_deleted" not in columns:
                conn.execute(
                    text(
                        f"ALTER TABLE {table_name} "
                        "ADD COLUMN is_deleted BOOLEAN DEFAULT 0"
                    )
                )
            if "deleted_at" not in columns:
                conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN deleted_at DATETIME"))
            if "deleted_by_user_id" not in columns:
                conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN deleted_by_user_id INTEGER"))

    if "todo_items" in table_names:
        todo_columns = {item["name"] for item in inspector.get_columns("todo_items")}
        if "my_day_date" not in todo_columns:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE todo_items ADD COLUMN my_day_date DATE"))

    if "billing_records" in table_names:
        billing_columns = {item["name"] for item in inspector.get_columns("billing_records")}
        with engine.begin() as conn:
            if "collection_start_date" not in billing_columns:
                conn.execute(
                    text(
                        "ALTER TABLE billing_records "
                        "ADD COLUMN collection_start_date VARCHAR(32) DEFAULT ''"
                    )
                )
            if "charge_category" not in billing_columns:
                conn.execute(
                    text(
                        "ALTER TABLE billing_records "
                        "ADD COLUMN charge_category VARCHAR(64) DEFAULT '代账'"
                    )
                )
            if "charge_mode" not in billing_columns:
                conn.execute(
                    text(
                        "ALTER TABLE billing_records "
                        "ADD COLUMN charge_mode VARCHAR(20) DEFAULT 'PERIODIC'"
                    )
                )
            if "amount_basis" not in billing_columns:
                conn.execute(
                    text(
                        "ALTER TABLE billing_records "
                        "ADD COLUMN amount_basis VARCHAR(20) DEFAULT 'MONTHLY'"
                    )
                )
            if "summary" not in billing_columns:
                conn.execute(
                    text(
                        "ALTER TABLE billing_records "
                        "ADD COLUMN summary VARCHAR(255) DEFAULT ''"
                    )
                )
            if "period_start_month" not in billing_columns:
                conn.execute(
                    text(
                        "ALTER TABLE billing_records "
                        "ADD COLUMN period_start_month VARCHAR(7) DEFAULT ''"
                    )
                )
            if "period_end_month" not in billing_columns:
                conn.execute(
                    text(
                        "ALTER TABLE billing_records "
                        "ADD COLUMN period_end_month VARCHAR(7) DEFAULT ''"
                    )
                )

    if "billing_activities" in table_names:
        activity_columns = {item["name"] for item in inspector.get_columns("billing_activities")}
        with engine.begin() as conn:
            if "receipt_account" not in activity_columns:
                conn.execute(
                    text(
                        "ALTER TABLE billing_activities "
                        "ADD COLUMN receipt_account VARCHAR(64) DEFAULT ''"
                    )
                )
            if "payment_id" not in activity_columns:
                conn.execute(
                    text(
                        "ALTER TABLE billing_activities "
                        "ADD COLUMN payment_id INTEGER"
                    )
                )

    if "billing_payments" in table_names:
        payment_columns = {item["name"] for item in inspector.get_columns("billing_payments")}
        if "receipt_account" not in payment_columns:
            with engine.begin() as conn:
                conn.execute(
                    text(
                        "ALTER TABLE billing_payments "
                        "ADD COLUMN receipt_account VARCHAR(64) DEFAULT ''"
                    )
                )

    if "leads" in table_names:
        lead_columns = {item["name"] for item in inspector.get_columns("leads")}
        if "related_customer_id" not in lead_columns:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE leads ADD COLUMN related_customer_id INTEGER"))

    if "address_resources" in table_names:
        address_columns = {item["name"] for item in inspector.get_columns("address_resources")}
        if "served_companies" not in address_columns:
            with engine.begin() as conn:
                conn.execute(
                    text(
                        "ALTER TABLE address_resources "
                        "ADD COLUMN served_companies TEXT DEFAULT ''"
                    )
                )

    if "users" in table_names:
        user_columns = {item["name"] for item in inspector.get_columns("users")}
        if "manager_user_id" not in user_columns:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE users ADD COLUMN manager_user_id INTEGER"))

    if "customers" in table_names:
        customer_columns = {item["name"] for item in inspector.get_columns("customers")}
        if "source_customer_id" not in customer_columns:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE customers ADD COLUMN source_customer_id INTEGER"))

    if "customer_timeline_events" in table_names:
        timeline_columns = {item["name"] for item in inspector.get_columns("customer_timeline_events")}
        with engine.begin() as conn:
            if "status" not in timeline_columns:
                conn.execute(
                    text(
                        "ALTER TABLE customer_timeline_events "
                        "ADD COLUMN status VARCHAR(16) DEFAULT 'NOTE'"
                    )
                )
            if "reminder_at" not in timeline_columns:
                conn.execute(text("ALTER TABLE customer_timeline_events ADD COLUMN reminder_at DATE"))
            if "completed_at" not in timeline_columns:
                conn.execute(text("ALTER TABLE customer_timeline_events ADD COLUMN completed_at DATE"))
            if "result" not in timeline_columns:
                conn.execute(
                    text(
                        "ALTER TABLE customer_timeline_events "
                        "ADD COLUMN result TEXT DEFAULT ''"
                    )
                )
            if "template_key" not in timeline_columns:
                conn.execute(
                    text(
                        "ALTER TABLE customer_timeline_events "
                        "ADD COLUMN template_key VARCHAR(32) DEFAULT ''"
                    )
                )

    if "common_library_items" in table_names:
        library_columns = {item["name"] for item in inspector.get_columns("common_library_items")}
        if "visibility" not in library_columns:
            with engine.begin() as conn:
                conn.execute(
                    text(
                        "ALTER TABLE common_library_items "
                        "ADD COLUMN visibility VARCHAR(16) DEFAULT 'INTERNAL'"
                    )
                )

    if "address_resources" in table_names and "address_resource_companies" in table_names:
        with engine.begin() as conn:
            migrated_resource_ids = {
                int(row[0])
                for row in conn.execute(
                    text("SELECT DISTINCT address_resource_id FROM address_resource_companies")
                ).fetchall()
                if row and row[0] is not None
            }
            resource_rows = conn.execute(
                text(
                    "SELECT id, served_companies FROM address_resources "
                    "WHERE served_companies IS NOT NULL AND trim(served_companies) != ''"
                )
            ).fetchall()
            for resource_id, served_companies in resource_rows:
                if int(resource_id) in migrated_resource_ids:
                    continue
                names = [
                    token.strip()
                    for token in re.split(r"[、,，\n]+", str(served_companies))
                    if token and token.strip()
                ]
                for name in names:
                    conn.execute(
                        text(
                            "INSERT INTO address_resource_companies "
                            "("
                            "address_resource_id, customer_id, company_name, notes, "
                            "created_at, updated_at, is_deleted, deleted_at, deleted_by_user_id"
                            ") "
                            "VALUES ("
                            ":address_resource_id, NULL, :company_name, '', "
                            "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, FALSE, NULL, NULL"
                            ")"
                        ),
                        {
                            "address_resource_id": int(resource_id),
                            "company_name": name,
                        },
                    )

    for soft_delete_table in [
        "users",
        "leads",
        "customers",
        "billing_records",
        "todo_items",
        "data_access_grants",
        "address_resources",
        "address_resource_companies",
        "common_library_items",
    ]:
        ensure_soft_delete_columns(soft_delete_table)


@app.on_event("startup")
def startup():
    if settings.reset_db_on_startup:
        Base.metadata.drop_all(bind=engine)

    Base.metadata.create_all(bind=engine)
    _ensure_schema_compatibility()

    if settings.bootstrap_demo_data:
        with SessionLocal() as db:
            bootstrap_data(db)


@app.get("/")
def root():
    return {"message": "账航·一帆财税 API is running"}
