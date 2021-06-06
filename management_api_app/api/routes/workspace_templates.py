from fastapi import APIRouter, Depends

from api.dependencies.database import get_repository
from db.repositories.workspace_templates import WorkspaceTemplateRepository
from models.schemas.workspace_template import WorkspaceTemplateNamesInList
from resources import strings


router = APIRouter()


@router.get("/workspace-templates", response_model=WorkspaceTemplateNamesInList, name=strings.API_GET_WORKSPACE_TEMPLATES)
async def retrieve_workspace_templates(workspace_template_repo: WorkspaceTemplateRepository = Depends(get_repository(WorkspaceTemplateRepository))) -> WorkspaceTemplateNamesInList:
    workspace_template_names = workspace_template_repo.get_workspace_template_names()
    return WorkspaceTemplateNamesInList(templateNames=workspace_template_names)
