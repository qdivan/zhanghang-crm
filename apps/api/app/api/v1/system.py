from fastapi import APIRouter

router = APIRouter(tags=["system"])


@router.get("/health")
def healthcheck():
    return {"status": "ok"}


@router.get("/meta")
def meta():
    return {
        "project": "daizhang-mvp",
        "version": "0.2.0",
        "scope": [
            "auth-rbac",
            "lead-followup-convert",
            "customer-assignment",
        ],
    }
