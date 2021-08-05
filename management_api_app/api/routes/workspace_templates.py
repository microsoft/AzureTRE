import logging

from fastapi import APIRouter, Depends, HTTPException
from starlette import status

from models.domain.resource_template import ResourceTemplate
from models.schemas.template import TemplateInCreate, TemplateInResponse
from models.schemas.workspace_service_template import WorkspaceServiceTemplateInCreate, \
    WorkspaceServiceTemplateInResponse
from services.authentication import get_current_admin_user
from api.dependencies.database import get_repository
from db.errors import EntityDoesNotExist
from db.repositories.workspace_templates import WorkspaceTemplateRepository
from models.schemas.workspace_template import (WorkspaceTemplateNamesInList, WorkspaceTemplateInCreate,
                                               WorkspaceTemplateInResponse)
from models.domain.resource import ResourceType
from resources import strings
from services.concatjsonschema import enrich_schema_defs, enrich_workspace_service_schema_defs

router = APIRouter(dependencies=[Depends(get_current_admin_user)])


@router.get("/workspace-templates", response_model=WorkspaceTemplateNamesInList,
            name=strings.API_GET_WORKSPACE_TEMPLATES)
async def get_workspace_templates(
        workspace_template_repo: WorkspaceTemplateRepository = Depends(get_repository(WorkspaceTemplateRepository))
) -> WorkspaceTemplateNamesInList:
    workspace_template_names = workspace_template_repo.get_workspace_template_names()
    return WorkspaceTemplateNamesInList(templateNames=workspace_template_names)


@router.post("/workspace-templates", status_code=status.HTTP_201_CREATED, response_model=WorkspaceTemplateInResponse,
             name=strings.API_CREATE_WORKSPACE_TEMPLATES)
async def create_workspace_template(
        workspace_template_create: WorkspaceTemplateInCreate,
        workspace_template_repo: WorkspaceTemplateRepository = Depends(get_repository(WorkspaceTemplateRepository)),
) -> TemplateInResponse:
    template_created = create_template_by_resource_type(workspace_template_create, workspace_template_repo, ResourceType.Workspace)
    template = enrich_schema_defs(template_created)
    return template


@router.post("/workspace-service-templates", status_code=status.HTTP_201_CREATED,
             response_model=WorkspaceServiceTemplateInResponse, name=strings.API_CREATE_WORKSPACE_SERVICE_TEMPLATES)
async def create_workspace_service_template(
        workspace_template_create: WorkspaceServiceTemplateInCreate,
        workspace_template_repo: WorkspaceTemplateRepository = Depends(get_repository(WorkspaceTemplateRepository)),
) -> TemplateInResponse:
    template_created = create_template_by_resource_type(workspace_template_create,
                                            workspace_template_repo,
                                            ResourceType.WorkspaceService)
    template = enrich_workspace_service_schema_defs(template_created)
    return template


@router.get("/workspace-templates/{template_name}", response_model=WorkspaceTemplateInResponse,
            name=strings.API_GET_WORKSPACE_TEMPLATE_BY_NAME)
async def get_current_workspace_template_by_name(
        template_name: str,
        workspace_template_repo: WorkspaceTemplateRepository = Depends(get_repository(WorkspaceTemplateRepository)),
) -> WorkspaceTemplateInResponse:
    try:
        template = workspace_template_repo.get_current_workspace_template_by_name(template_name)
        template = enrich_schema_defs(template)
        return template
    except EntityDoesNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=strings.WORKSPACE_TEMPLATE_DOES_NOT_EXIST)
    except Exception as e:
        logging.debug(e)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail=strings.STATE_STORE_ENDPOINT_NOT_RESPONDING)


def create_template_by_resource_type(workspace_template_create: TemplateInCreate,
                                     workspace_template_repo: WorkspaceTemplateRepository,
                                     resource_type: ResourceType) -> ResourceTemplate:
    try:
        template = workspace_template_repo.get_workspace_template_by_name_and_version(workspace_template_create.name,
                                                                                      workspace_template_create.version)
        if template:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=strings.WORKSPACE_TEMPLATE_VERSION_EXISTS)
    except EntityDoesNotExist:
        try:
            template = workspace_template_repo.get_current_workspace_template_by_name(workspace_template_create.name)
            if workspace_template_create.current:
                template.current = False
                workspace_template_repo.update_item(template)
        except EntityDoesNotExist:
            # first registration
            workspace_template_create.current = True  # For first time registration, template is always marked current
        return workspace_template_repo.create_workspace_template_item(workspace_template_create, resource_type)

