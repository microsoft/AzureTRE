from fastapi import APIRouter

from api.routes import health, status, workspaces, workspace_templates


router = APIRouter()
router.include_router(health.router, tags=["health"])
router.include_router(workspace_templates.router, tags=["workspace-templates"])
router.include_router(workspaces.router, tags=["workspaces"])
router.include_router(status.router, tags=["status"])
