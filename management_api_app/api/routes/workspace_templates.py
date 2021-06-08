from fastapi import APIRouter, Depends
from starlette import status

from api.dependencies.database import get_repository
from db.repositories.workspace_templates import WorkspaceTemplateRepository
from models.schemas.workspace_template import WorkspaceTemplateNamesInList, WorkspaceTemplateIdInResponse, WorkspaceTemplateInCreate
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
    pass
