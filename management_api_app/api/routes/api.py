from fastapi import APIRouter

from api.routes import health, status


router = APIRouter()
router.include_router(health.router, tags=["health"])
router.include_router(status.router, tags=["status"])
