import logging

from fastapi import APIRouter, Depends, HTTPException
from starlette import status

from api.dependencies.database import get_repository
from db.errors import EntityDoesNotExist
from db.repositories.workspace_templates import WorkspaceTemplateRepository
from models.schemas.workspace_template import (
    WorkspaceTemplateNamesInList,
    WorkspaceTemplateIdInResponse,
    WorkspaceTemplateInCreate,
    WorkspaceTemplateInResponse
)
from resources import strings


router = APIRouter()


@router.get("/workspace-templates", response_model=WorkspaceTemplateNamesInList, name=strings.API_GET_WORKSPACE_TEMPLATES)
async def get_workspace_templates(workspace_template_repo: WorkspaceTemplateRepository = Depends(get_repository(WorkspaceTemplateRepository))) -> WorkspaceTemplateNamesInList:
    workspace_template_names = workspace_template_repo.get_workspace_template_names()
    return WorkspaceTemplateNamesInList(templateNames=workspace_template_names)


@router.post("/workspace-templates", status_code=status.HTTP_201_CREATED,
             response_model=WorkspaceTemplateIdInResponse,
             name=strings.API_CREATE_WORKSPACE_TEMPLATES)
async def create_workspace_template(workspace_template_create: WorkspaceTemplateInCreate, workspace_template_repo: WorkspaceTemplateRepository =
                                    Depends(get_repository(WorkspaceTemplateRepository))) -> WorkspaceTemplateIdInResponse:
    create_new_current = workspace_template_create.current
    if create_new_current:
        try:
            template = workspace_template_repo.get_current_workspace_template_by_name(workspace_template_create.name)
        except EntityDoesNotExist:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=strings.WORKSPACE_TEMPLATE_DOES_NOT_EXIST)
    else:
        try:
            template = workspace_template_repo.get_workspace_template_by_name_and_version(workspace_template_create.name,
                                                                                          workspace_template_create.version)
            if template:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=strings.WORKSPACE_TEMPLATE_VERSION_EXISTS)
        except EntityDoesNotExist:
            pass


@router.get("/workspace-templates/{template_name}", response_model=WorkspaceTemplateInResponse, name=strings.API_GET_WORKSPACE_TEMPLATE_BY_NAME)
async def get_current_workspace_template_by_name(template_name: str, workspace_template_repo: WorkspaceTemplateRepository = Depends(get_repository(WorkspaceTemplateRepository))) -> WorkspaceTemplateInResponse:
    try:
        template = workspace_template_repo.get_current_workspace_template_by_name(template_name)
        return WorkspaceTemplateInResponse(workspaceTemplate=template)
    except EntityDoesNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=strings.WORKSPACE_TEMPLATE_DOES_NOT_EXIST)
    except Exception as e:
        logging.debug(e)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=strings.STATE_STORE_ENDPOINT_NOT_RESPONDING)
