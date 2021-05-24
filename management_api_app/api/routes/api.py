from fastapi import APIRouter

from api.routes import ping, health, workspaces


router = APIRouter()
router.include_router(ping.router, tags=["ping"])
router.include_router(health.router, tags=["health"])
router.include_router(workspaces.router, tags=["workspaces"])
