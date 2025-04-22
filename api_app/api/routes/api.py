from collections import defaultdict
from typing import Any, DefaultDict, Dict, Optional

from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.openapi.docs import get_swagger_ui_html, get_swagger_ui_oauth2_redirect_html
from fastapi.openapi.utils import get_openapi

from api.helpers import get_repository
from db.repositories.workspaces import WorkspaceRepository
from api.routes import health, ping, workspaces, workspace_templates, workspace_service_templates, user_resource_templates, \
    shared_services, shared_service_templates, migrations, costs, airlock, operations, metadata, requests, workspace_users
from core import config
from resources import strings

core_tags_metadata = [
    {"name": "health", "description": "Verify that the TRE is up and running"},
    {"name": "workspace templates", "description": "**TRE admin** registers and can access templates"},
    {"name": "workspace service templates", "description": "**TRE admin** registers templates and can access templates"},
    {"name": "user resource templates", "description": "**TRE admin** registers templates and can access templates"},
    {"name": "workspaces", "description": "**TRE admin** administers workspaces, **TRE Users** can view their own workspaces"},
]

workspace_tags_metadata = [
    {"name": "workspaces", "description": " **Workspace Owners and Researchers** can view their own workspaces"},
    {"name": "workspace services", "description": "**Workspace Owners** administer workspace services, **Workspace Owners and Researchers** can view services in the workspaces they belong to"},
    {"name": "user resources", "description": "**Researchers** administer and can view their own researchers, **Workspace Owners** can view/update/delete all user resources in their workspaces"},
    {"name": "shared services", "description": "**TRE administratiors** administer shared services"}
]

# Root
router = APIRouter()
router.include_router(health.router, tags=["health"])
router.include_router(ping.router, tags=["health"])
router.include_router(metadata.router, tags=["metadata"])

# Core API
core_router = APIRouter(prefix=config.API_PREFIX)
core_router.include_router(health.router, tags=["health"])
core_router.include_router(ping.router, tags=["health"])
core_router.include_router(metadata.router, tags=["metadata"])
core_router.include_router(workspace_templates.workspace_templates_admin_router, tags=["workspace templates"])
core_router.include_router(workspace_service_templates.workspace_service_templates_core_router, tags=["workspace service templates"])
core_router.include_router(user_resource_templates.user_resource_templates_core_router, tags=["user resource templates"])
core_router.include_router(shared_service_templates.shared_service_templates_core_router, tags=["shared service templates"])
core_router.include_router(shared_services.shared_services_router, tags=["shared services"])
core_router.include_router(operations.operations_router, tags=["operations"])
core_router.include_router(workspaces.workspaces_core_router, tags=["workspaces"])
core_router.include_router(workspaces.workspaces_shared_router, tags=["workspaces"])
core_router.include_router(migrations.migrations_core_router, tags=["migrations"])
core_router.include_router(costs.costs_core_router, tags=["costs"])
core_router.include_router(costs.costs_workspace_router, tags=["costs"])
core_router.include_router(requests.router, tags=["requests"])
core_router.include_router(workspace_users.workspaces_users_shared_router, tags=["users"])

if config.USER_MANAGEMENT_ENABLED:
    core_router.include_router(workspace_users.workspaces_users_admin_router, tags=["users"])

core_swagger_router = APIRouter()
swagger_disabled_router = APIRouter()

openapi_definitions: DefaultDict[str, Optional[Dict[str, Any]]] = defaultdict(lambda: None)


@core_swagger_router.get("/openapi.json", include_in_schema=False, name="core_openapi")
async def core_openapi(request: Request):
    global openapi_definitions

    if openapi_definitions["core"] is None:
        openapi_definitions["core"] = get_openapi(
            title=f"{config.PROJECT_NAME}",
            description=config.API_DESCRIPTION,
            version=config.VERSION,
            routes=core_router.routes,
            tags=core_tags_metadata
        )

    return openapi_definitions["core"]


@core_swagger_router.get('/docs/oauth2-redirect', include_in_schema=False)
async def swagger_ui_redirect():
    return get_swagger_ui_oauth2_redirect_html()


@core_swagger_router.get("/docs", include_in_schema=False, name="core_swagger")
async def get_swagger(request: Request):
    swagger_ui_html = get_swagger_ui_html(
        openapi_url="openapi.json",
        title=request.app.title + " - Swagger UI",
        oauth2_redirect_url="/api/docs/oauth2-redirect",
        init_oauth={
            "usePkceWithAuthorizationCodeGrant": True,
            "clientId": config.SWAGGER_UI_CLIENT_ID,
            "scopes": ["openid", "offline_access", config.API_ROOT_SCOPE]
        }
    )

    return swagger_ui_html


@swagger_disabled_router.get("/docs", include_in_schema=False, name="swagger_disabled")
async def get_disabled_swagger():
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=strings.SWAGGER_DISABLED)


# Workspace API
workspace_router = APIRouter(prefix=config.API_PREFIX)
workspace_router.include_router(workspaces.workspaces_shared_router, tags=["workspaces"])
workspace_router.include_router(workspaces.workspace_services_workspace_router, tags=["workspace services"])
workspace_router.include_router(workspaces.user_resources_workspace_router, tags=["user resources"])
workspace_router.include_router(costs.costs_workspace_router, tags=["workspace costs"])
workspace_router.include_router(airlock.airlock_workspace_router, tags=["airlock"])

workspace_swagger_router = APIRouter()
workspace_swagger_disabled_router = APIRouter()


def get_scope(workspace) -> str:
    # Cope with the fact that scope id can have api:// at the front.
    return f"api://{workspace.properties['scope_id'].replace('api://', '')}/user_impersonation"


@workspace_swagger_router.get("/workspaces/{workspace_id}/openapi.json", include_in_schema=False, name="openapi_definitions")
async def get_openapi_json(workspace_id: str, request: Request, workspace_repo=Depends(get_repository(WorkspaceRepository))):
    global openapi_definitions

    if openapi_definitions[workspace_id] is None:

        openapi_definitions[workspace_id] = get_openapi(
            title=f"{config.PROJECT_NAME} - Workspace {workspace_id}",
            description=config.API_DESCRIPTION,
            version=config.VERSION,
            routes=workspace_router.routes,
            tags=workspace_tags_metadata
        )

        workspace = await workspace_repo.get_workspace_by_id(workspace_id)
        scope = {get_scope(workspace): "List and Get TRE Workspaces"}

        openapi_definitions[workspace_id]['components']['securitySchemes']['oauth2']['flows']['authorizationCode']['scopes'] = scope

        # Add an example into every workspace_id path parameter so users don't have to cut and paste them in.
        for route in openapi_definitions[workspace_id]['paths'].values():
            for verb in route.values():
                # We now have a list of parameters for each route
                for parameter in verb['parameters']:
                    if (parameter['name'] == 'workspace_id'):
                        parameter['schema']['example'] = workspace_id

    return openapi_definitions[workspace_id]


@workspace_swagger_router.get("/workspaces/{workspace_id}/docs", include_in_schema=False, name="workspace_swagger")
async def get_workspace_swagger(workspace_id, request: Request, workspace_repo=Depends(get_repository(WorkspaceRepository))):

    workspace = await workspace_repo.get_workspace_by_id(workspace_id)
    scope = get_scope(workspace)
    swagger_ui_html = get_swagger_ui_html(
        openapi_url="openapi.json",
        title=request.app.title + " - Swagger UI",
        oauth2_redirect_url="/api/docs/oauth2-redirect",
        init_oauth={
            "usePkceWithAuthorizationCodeGrant": True,
            "clientId": config.SWAGGER_UI_CLIENT_ID,
            "scopes": ["openid", "offline_access", scope]
        }
    )

    return swagger_ui_html


@workspace_swagger_disabled_router.get("/workspaces/{workspace_id}/docs", include_in_schema=False, name="workspace_swagger_disabled")
async def get_disabled_workspace_swagger():
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=strings.SWAGGER_DISABLED)


if config.ENABLE_SWAGGER:
    core_router.include_router(core_swagger_router)
    workspace_router.include_router(workspace_swagger_router)
else:
    core_router.include_router(swagger_disabled_router)
    workspace_router.include_router(workspace_swagger_disabled_router)

router.include_router(core_router)
router.include_router(workspace_router)
