from fastapi import APIRouter

from api.routes import health, status, workspaces, workspace_templates, workspace_service_templates


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
router.include_router(health.router, tags=["health"])
router.include_router(workspace_templates.router, tags=["workspace templates"])
router.include_router(workspace_service_templates.service_templates_router, tags=["workspace service templates"])
router.include_router(workspace_service_templates.user_resource_templates_router, tags=["user resource templates"])
router.include_router(workspaces.workspaces_router, tags=["workspaces"])
router.include_router(workspaces.workspace_services_router, tags=["workspace services"])
router.include_router(workspaces.user_resources_router, tags=["user resources"])
router.include_router(status.router, tags=["status"])
