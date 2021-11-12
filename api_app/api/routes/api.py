from fastapi import APIRouter

from api.routes import health, status, workspaces, workspace_templates, workspace_service_templates
from core import config

tags_metadata = [
    {"name": "health", "description": "Verify that the API is up and running"},
    {"name": "workspace templates", "description": "**TRE admin** registers and can access templates"},
    {"name": "workspace service templates", "description": "**TRE admin** registers templates, all **TRE users** can access templates"},
    {"name": "user resource templates", "description": "**TRE admin** registers templates, all **TRE users** can access templates"},
    {"name": "workspaces", "description": "**TRE admin** administers workspaces, **Workspace Owners and Researchers** can view their own workspaces"},
    {"name": "workspace services", "description": "**Workspace Owners** administer workspace services, **Workspace Owners and Researchers** can view services in the workspaces they belong to"},
    {"name": "user resources", "description": "**Researchers** administer and can view their own researchers, **Workspace Owners** can view/update/delete all user resources in their workspaces"},
    {"name": "status", "description": "Status of API and related resources"},
]


router = APIRouter()
core_router = APIRouter(prefix=config.API_PREFIX)
core_router.include_router(health.router, tags=["health"])
core_router.include_router(workspace_templates.router, tags=["workspace templates"])
core_router.include_router(workspace_service_templates.workspace_service_templates_router, tags=["workspace service templates"])
core_router.include_router(workspace_service_templates.user_resource_templates_router, tags=["user resource templates"])
core_router.include_router(status.router, tags=["status"])
core_router.include_router(workspaces.tre_router, tags=["workspaces"])

router.include_router(core_router)
router.include_router(workspaces.workspace_router)
