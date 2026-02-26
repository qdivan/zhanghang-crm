from fastapi import APIRouter

from app.api.v1.admin import router as admin_router
from app.api.v1.address_resources import router as address_resource_router
from app.api.v1.auth import router as auth_router
from app.api.v1.billing import router as billing_router
from app.api.v1.customers import router as customer_router
from app.api.v1.leads import router as lead_router
from app.api.v1.system import router as system_router
from app.api.v1.users import router as user_router

router = APIRouter()
router.include_router(system_router)
router.include_router(auth_router)
router.include_router(user_router)
router.include_router(admin_router)
router.include_router(lead_router)
router.include_router(customer_router)
router.include_router(address_resource_router)
router.include_router(billing_router)
