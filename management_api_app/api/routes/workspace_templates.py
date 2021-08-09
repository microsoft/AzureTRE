import logging

from fastapi import APIRouter, Depends, HTTPException
from starlette import status

from api.dependencies.database import get_repository
from db.errors import EntityDoesNotExist, EntityVersionExist
from db.repositories.resource_templates import ResourceTemplateRepository
from models.domain.resource import ResourceType
from models.schemas.resource_template import ResourceTemplateInResponse
from models.schemas.workspace_template import WorkspaceTemplateNamesInList, WorkspaceTemplateInCreate, WorkspaceTemplateInResponse
from resources import strings
from services.authentication import get_current_admin_user
from services.concatjsonschema import enrich_workspace_schema_defs
from services.resource_template_service import create_template_by_resource_type


router = APIRouter(dependencies=[Depends(get_current_admin_user)])


@router.get("/workspace-templates", response_model=WorkspaceTemplateNamesInList,
            name=strings.API_GET_WORKSPACE_TEMPLATES)
async def get_workspace_templates(
        workspace_template_repo: ResourceTemplateRepository = Depends(get_repository(ResourceTemplateRepository))
) -> WorkspaceTemplateNamesInList:
    workspace_template_names = workspace_template_repo.get_workspace_template_names()
    return WorkspaceTemplateNamesInList(templateNames=workspace_template_names)


@router.post("/workspace-templates", status_code=status.HTTP_201_CREATED, response_model=WorkspaceTemplateInResponse,
             name=strings.API_CREATE_WORKSPACE_TEMPLATES)
async def create_workspace_template(
        workspace_template_create: WorkspaceTemplateInCreate,
        workspace_template_repo: ResourceTemplateRepository = Depends(get_repository(ResourceTemplateRepository)),
) -> ResourceTemplateInResponse:
    try:
        template_created = create_template_by_resource_type(workspace_template_create,
                                                            workspace_template_repo,
                                                            ResourceType.Workspace)
        template = enrich_workspace_schema_defs(template_created)
        return template
    except EntityVersionExist:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=strings.WORKSPACE_TEMPLATE_VERSION_EXISTS)


@router.get("/workspace-templates/{template_name}", response_model=WorkspaceTemplateInResponse,
            name=strings.API_GET_WORKSPACE_TEMPLATE_BY_NAME)
async def get_current_workspace_template_by_name(
        template_name: str,
        workspace_template_repo: ResourceTemplateRepository = Depends(get_repository(ResourceTemplateRepository)),
) -> WorkspaceTemplateInResponse:
    try:
        template = workspace_template_repo.get_current_resource_template_by_name(template_name)
        template = enrich_workspace_schema_defs(template)
        return template
    except EntityDoesNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=strings.WORKSPACE_TEMPLATE_DOES_NOT_EXIST)
    except Exception as e:
        logging.debug(e)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail=strings.STATE_STORE_ENDPOINT_NOT_RESPONDING)
