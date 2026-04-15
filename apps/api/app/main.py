import re
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text
from sqlalchemy.engine.url import make_url

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


def _reset_database_storage() -> None:
    engine.dispose()
    if engine.dialect.name == "sqlite":
        with engine.begin() as conn:
            conn.execute(text("PRAGMA foreign_keys=OFF"))
            table_names = conn.execute(
                text(
                    "SELECT name FROM sqlite_master "
                    "WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                )
            ).scalars().all()
            for table_name in table_names:
                safe_name = str(table_name).replace('"', '""')
                conn.execute(text(f'DROP TABLE IF EXISTS "{safe_name}"'))
            conn.execute(text("PRAGMA foreign_keys=ON"))
        db_url = make_url(settings.database_url)
        db_path = db_url.database
        if db_path and db_path != ":memory:":
            target_path = Path(db_path)
            if not target_path.is_absolute():
                target_path = Path.cwd() / target_path
            journal_path = target_path.with_suffix(f"{target_path.suffix}-journal")
            if journal_path.exists():
                journal_path.unlink()
        engine.dispose()
        return
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def _ensure_schema_compatibility() -> None:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    dialect_name = engine.dialect.name

    def ensure_soft_delete_columns(table_name: str) -> None:
        if table_name not in table_names:
            return
        columns = {item["name"] for item in inspector.get_columns(table_name)}
        with engine.begin() as conn:
            if "is_deleted" not in columns:
                conn.execute(
                    text(
                        f"ALTER TABLE {table_name} "
                        "ADD COLUMN is_deleted BOOLEAN DEFAULT FALSE"
                    )
                )
            if "deleted_at" not in columns:
                conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN deleted_at TIMESTAMP"))
            if "deleted_by_user_id" not in columns:
                conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN deleted_by_user_id INTEGER"))

    def ensure_customer_responsibility_columns() -> None:
        if "customers" not in table_names:
            return
        customer_columns_info = inspector.get_columns("customers")
        customer_columns = {item["name"]: item for item in customer_columns_info}

        needs_sqlite_rebuild = dialect_name == "sqlite" and (
            "responsible_user_id" not in customer_columns
            or not customer_columns.get("assigned_accountant_id", {}).get("nullable", True)
        )
        if needs_sqlite_rebuild:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE customers RENAME TO customers__legacy"))
                conn.execute(
                    text(
                        """
                        CREATE TABLE customers (
                            id INTEGER NOT NULL PRIMARY KEY,
                            name VARCHAR(200) NOT NULL,
                            contact_name VARCHAR(100) NOT NULL,
                            phone VARCHAR(32) NOT NULL,
                            status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
                            responsible_user_id INTEGER,
                            assigned_accountant_id INTEGER,
                            customer_code_seq INTEGER,
                            customer_code_suffix VARCHAR(8) DEFAULT '',
                            customer_code VARCHAR(32) DEFAULT '',
                            source_customer_id INTEGER,
                            source_lead_id INTEGER NOT NULL UNIQUE,
                            created_at DATETIME,
                            is_deleted BOOLEAN DEFAULT FALSE,
                            deleted_at TIMESTAMP,
                            deleted_by_user_id INTEGER,
                            FOREIGN KEY(responsible_user_id) REFERENCES users (id),
                            FOREIGN KEY(assigned_accountant_id) REFERENCES users (id),
                            FOREIGN KEY(source_lead_id) REFERENCES leads (id)
                        )
                        """
                    )
                )
                responsible_select = (
                    "COALESCE(responsible_user_id, assigned_accountant_id)"
                    if "responsible_user_id" in customer_columns
                    else "assigned_accountant_id"
                )
                source_customer_select = "source_customer_id" if "source_customer_id" in customer_columns else "NULL"
                code_seq_select = "customer_code_seq" if "customer_code_seq" in customer_columns else "NULL"
                code_suffix_select = "COALESCE(customer_code_suffix, '')" if "customer_code_suffix" in customer_columns else "''"
                code_select = "COALESCE(customer_code, '')" if "customer_code" in customer_columns else "''"
                is_deleted_select = "COALESCE(is_deleted, FALSE)" if "is_deleted" in customer_columns else "FALSE"
                deleted_at_select = "deleted_at" if "deleted_at" in customer_columns else "NULL"
                deleted_by_select = "deleted_by_user_id" if "deleted_by_user_id" in customer_columns else "NULL"
                created_at_select = "COALESCE(created_at, CURRENT_TIMESTAMP)" if "created_at" in customer_columns else "CURRENT_TIMESTAMP"
                conn.execute(
                    text(
                        f"""
                        INSERT INTO customers (
                            id, name, contact_name, phone, status,
                            responsible_user_id, assigned_accountant_id,
                            customer_code_seq, customer_code_suffix, customer_code,
                            source_customer_id, source_lead_id, created_at,
                            is_deleted, deleted_at, deleted_by_user_id
                        )
                        SELECT
                            id,
                            name,
                            contact_name,
                            phone,
                            COALESCE(status, 'ACTIVE'),
                            {responsible_select},
                            assigned_accountant_id,
                            {code_seq_select},
                            {code_suffix_select},
                            {code_select},
                            {source_customer_select},
                            source_lead_id,
                            {created_at_select},
                            {is_deleted_select},
                            {deleted_at_select},
                            {deleted_by_select}
                        FROM customers__legacy
                        """
                    )
                )
                conn.execute(text("DROP TABLE customers__legacy"))
                for statement in [
                    "CREATE INDEX IF NOT EXISTS ix_customers_name ON customers (name)",
                    "CREATE INDEX IF NOT EXISTS ix_customers_phone ON customers (phone)",
                    "CREATE INDEX IF NOT EXISTS ix_customers_responsible_user_id ON customers (responsible_user_id)",
                    "CREATE INDEX IF NOT EXISTS ix_customers_assigned_accountant_id ON customers (assigned_accountant_id)",
                    "CREATE INDEX IF NOT EXISTS ix_customers_customer_code_seq ON customers (customer_code_seq)",
                    "CREATE INDEX IF NOT EXISTS ix_customers_customer_code ON customers (customer_code)",
                    "CREATE INDEX IF NOT EXISTS ix_customers_source_customer_id ON customers (source_customer_id)",
                    "CREATE INDEX IF NOT EXISTS ix_customers_created_at ON customers (created_at)",
                    "CREATE INDEX IF NOT EXISTS ix_customers_is_deleted ON customers (is_deleted)",
                    "CREATE INDEX IF NOT EXISTS ix_customers_deleted_at ON customers (deleted_at)",
                    "CREATE INDEX IF NOT EXISTS ix_customers_deleted_by_user_id ON customers (deleted_by_user_id)",
                ]:
                    conn.execute(text(statement))
            return

        with engine.begin() as conn:
            if "responsible_user_id" not in customer_columns:
                conn.execute(text("ALTER TABLE customers ADD COLUMN responsible_user_id INTEGER"))
            if "source_customer_id" not in customer_columns:
                conn.execute(text("ALTER TABLE customers ADD COLUMN source_customer_id INTEGER"))
            if "customer_code_seq" not in customer_columns:
                conn.execute(text("ALTER TABLE customers ADD COLUMN customer_code_seq INTEGER"))
            if "customer_code_suffix" not in customer_columns:
                conn.execute(text("ALTER TABLE customers ADD COLUMN customer_code_suffix VARCHAR(8) DEFAULT ''"))
            if "customer_code" not in customer_columns:
                conn.execute(text("ALTER TABLE customers ADD COLUMN customer_code VARCHAR(32) DEFAULT ''"))
            conn.execute(
                text(
                    "UPDATE customers "
                    "SET responsible_user_id = assigned_accountant_id "
                    "WHERE responsible_user_id IS NULL"
                )
            )
            if dialect_name == "postgresql" and not customer_columns.get("assigned_accountant_id", {}).get("nullable", True):
                conn.execute(text("ALTER TABLE customers ALTER COLUMN assigned_accountant_id DROP NOT NULL"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_customers_responsible_user_id ON customers (responsible_user_id)"))

    def ensure_billing_assignment_kind() -> None:
        if "billing_assignments" not in table_names:
            return
        assignment_columns = {item["name"] for item in inspector.get_columns("billing_assignments")}
        with engine.begin() as conn:
            if "assignment_kind" not in assignment_columns:
                conn.execute(
                    text(
                        "ALTER TABLE billing_assignments "
                        "ADD COLUMN assignment_kind VARCHAR(16) DEFAULT 'CC'"
                    )
                )
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_billing_assignments_assignment_kind ON billing_assignments (assignment_kind)"))
            rows = conn.execute(
                text(
                    "SELECT id, billing_record_id, is_active "
                    "FROM billing_assignments "
                    "ORDER BY billing_record_id ASC, is_active DESC, id DESC"
                )
            ).fetchall()
            primary_record_ids: set[int] = set()
            for row in rows:
                assignment_id = int(row[0])
                record_id = int(row[1])
                is_active = bool(row[2])
                expected_kind = "CC"
                if is_active and record_id not in primary_record_ids:
                    expected_kind = "PRIMARY"
                    primary_record_ids.add(record_id)
                conn.execute(
                    text("UPDATE billing_assignments SET assignment_kind = :assignment_kind WHERE id = :assignment_id"),
                    {"assignment_kind": expected_kind, "assignment_id": assignment_id},
                )

    def ensure_user_sso_columns() -> None:
        if "users" not in table_names:
            return
        user_columns = {item["name"] for item in inspector.get_columns("users")}
        with engine.begin() as conn:
            if "email" not in user_columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN email VARCHAR(255) DEFAULT ''"))
            if "display_name" not in user_columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN display_name VARCHAR(255) DEFAULT ''"))
            if "external_managed" not in user_columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN external_managed BOOLEAN DEFAULT FALSE"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_users_email ON users (email)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_users_external_managed ON users (external_managed)"))

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
        with engine.begin() as conn:
            if "receipt_account" not in payment_columns:
                conn.execute(
                    text(
                        "ALTER TABLE billing_payments "
                        "ADD COLUMN receipt_account VARCHAR(64) DEFAULT ''"
                    )
                )
            if "is_prepay" not in payment_columns:
                conn.execute(
                    text(
                        "ALTER TABLE billing_payments "
                        "ADD COLUMN is_prepay BOOLEAN DEFAULT FALSE"
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
        ensure_customer_responsibility_columns()

    ensure_billing_assignment_kind()

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
        "billing_payments",
        "todo_items",
        "data_access_grants",
        "address_resources",
        "address_resource_companies",
        "common_library_items",
    ]:
        ensure_soft_delete_columns(soft_delete_table)

    ensure_user_sso_columns()


@app.on_event("startup")
def startup():
    if settings.reset_db_on_startup:
        _reset_database_storage()

    Base.metadata.create_all(bind=engine)
    engine.dispose()
    if not settings.reset_db_on_startup:
        _ensure_schema_compatibility()
        engine.dispose()

    if settings.bootstrap_demo_data:
        with SessionLocal() as db:
            bootstrap_data(db)


@app.get("/")
def root():
    return {"message": "账航·一帆财税 API is running"}
