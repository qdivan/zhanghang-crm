from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from app.api.v1.router import router as v1_router
from app.core.config import settings
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.services.bootstrap import bootstrap_data
import app.models  # noqa: F401

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

    if "leads" in table_names:
        lead_columns = {item["name"] for item in inspector.get_columns("leads")}
        if "related_customer_id" not in lead_columns:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE leads ADD COLUMN related_customer_id INTEGER"))


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
