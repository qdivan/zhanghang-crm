from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings


connect_args = {}
engine_kwargs = {}
if settings.database_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False
    if settings.environment == "test" or settings.reset_db_on_startup:
        engine_kwargs["poolclass"] = NullPool

engine = create_engine(
    settings.database_url,
    future=True,
    pool_pre_ping=True,
    connect_args=connect_args,
    **engine_kwargs,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
