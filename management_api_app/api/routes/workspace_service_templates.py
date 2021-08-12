import logging

from fastapi import APIRouter, Depends, HTTPException
from starlette import status

from api.dependencies.database import get_repository
from api.dependencies.workspace_service_templates import get_workspace_service_template_by_name_from_path
from db.errors import EntityVersionExist, EntityDoesNotExist
from db.repositories.resource_templates import ResourceTemplateRepository
from db.repositories.user_resource_templates import UserResourceTemplateRepository
from models.domain.resource import ResourceType
from models.domain.resource_template import ResourceTemplate
from models.schemas.user_resource_template import UserResourceTemplateInResponse, UserResourceTemplateInCreate
from models.schemas.resource_template import ResourceTemplateInResponse, ResourceTemplateInformationInList
from models.schemas.workspace_service_template import WorkspaceServiceTemplateInCreate, WorkspaceServiceTemplateInResponse
from resources import strings
from services.authentication import get_current_admin_user
from services.concatjsonschema import enrich_workspace_service_schema_defs
from services.resource_template_service import create_template_by_resource_type, create_user_resource_template


router = APIRouter(dependencies=[Depends(get_current_admin_user)])


@router.get("/workspace-service-templates", response_model=ResourceTemplateInformationInList, name=strings.API_GET_WORKSPACE_SERVICE_TEMPLATES)
async def get_workspace_service_templates(
        workspace_service_template_repo: ResourceTemplateRepository = Depends(get_repository(ResourceTemplateRepository))
) -> ResourceTemplateInformationInList:
    workspace_service_templates = workspace_service_template_repo.get_basic_resource_templates_information(ResourceType.WorkspaceService)
    return ResourceTemplateInformationInList(templates=workspace_service_templates)


@router.get("/workspace-service-templates/{template_name}", response_model=WorkspaceServiceTemplateInResponse, name=strings.API_GET_WORKSPACE_SERVICE_TEMPLATE_BY_NAME)
async def get_current_workspace_template_by_name(
        template_name: str,
        workspace_service_template_repo: ResourceTemplateRepository = Depends(get_repository(ResourceTemplateRepository))
) -> WorkspaceServiceTemplateInResponse:
    try:
        template = workspace_service_template_repo.get_current_resource_template_by_name(template_name, ResourceType.WorkspaceService)
        template = enrich_workspace_service_schema_defs(template)
        return template
    except EntityDoesNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=strings.TEMPLATE_DOES_NOT_EXIST)
    except Exception as e:
        logging.debug(e)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=strings.STATE_STORE_ENDPOINT_NOT_RESPONDING)


@router.post("/workspace-service-templates", status_code=status.HTTP_201_CREATED,
             response_model=WorkspaceServiceTemplateInResponse, name=strings.API_CREATE_WORKSPACE_SERVICE_TEMPLATES)
async def register_workspace_service_template(
        workspace_template_create: WorkspaceServiceTemplateInCreate,
        workspace_template_repo: ResourceTemplateRepository = Depends(get_repository(ResourceTemplateRepository)),
) -> ResourceTemplateInResponse:
    try:
        template_created = create_template_by_resource_type(workspace_template_create,
                                                            workspace_template_repo,
                                                            ResourceType.WorkspaceService)
        template = enrich_workspace_service_schema_defs(template_created)
        return template
    except EntityVersionExist:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=strings.WORKSPACE_TEMPLATE_VERSION_EXISTS)


@router.post("/workspace-service-templates/{template_name}/user-resource-templates",
             status_code=status.HTTP_201_CREATED,
             response_model=UserResourceTemplateInResponse, name=strings.API_CREATE_USER_RESOURCE_TEMPLATES)
async def register_user_resource_template(
        user_resource_template_create: UserResourceTemplateInCreate,
        user_resource_template_repo: UserResourceTemplateRepository = Depends(get_repository(UserResourceTemplateRepository)),
        workspace_service_template: ResourceTemplate = Depends(get_workspace_service_template_by_name_from_path)
) -> UserResourceTemplateInResponse:
    try:
        template_created = create_user_resource_template(user_resource_template_create,
                                                         user_resource_template_repo,
                                                         workspace_service_template.name)
        enriched_template = enrich_workspace_service_schema_defs(template_created)
        return enriched_template
    except EntityVersionExist:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=strings.WORKSPACE_TEMPLATE_VERSION_EXISTS)
