from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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


@app.on_event("startup")
def startup():
    if settings.reset_db_on_startup:
        Base.metadata.drop_all(bind=engine)

    Base.metadata.create_all(bind=engine)

    if settings.bootstrap_demo_data:
        with SessionLocal() as db:
            bootstrap_data(db)


@app.get("/")
def root():
    return {"message": "账航·一帆财税 API is running"}
