from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import TypeAdapter

from api.helpers import get_repository
from db.repositories.resource_templates import ResourceTemplateRepository
from models.domain.resource import ResourceType
from models.schemas.resource_template import ResourceTemplateInformationInList
from models.schemas.workspace_template import WorkspaceTemplateInResponse
from resources import strings
from services.authentication import get_current_admin_user
from api.routes.resource_helpers import get_template


workspace_templates_admin_router = APIRouter(dependencies=[Depends(get_current_admin_user)])


@workspace_templates_admin_router.get("/workspace-templates", response_model=ResourceTemplateInformationInList, name=strings.API_GET_WORKSPACE_TEMPLATES)
async def get_workspace_templates(authorized_only: bool = False, template_repo=Depends(get_repository(ResourceTemplateRepository)), user=Depends(get_current_admin_user)) -> ResourceTemplateInformationInList:
    templates_infos = await template_repo.get_templates_information(ResourceType.Workspace, user.roles if authorized_only else None)
    return ResourceTemplateInformationInList(templates=templates_infos)


@workspace_templates_admin_router.get("/workspace-templates/{workspace_template_name}", response_model=WorkspaceTemplateInResponse, name=strings.API_GET_WORKSPACE_TEMPLATE_BY_NAME, response_model_exclude_none=True)
async def get_workspace_template(workspace_template_name: str, is_update: bool = False, version: Optional[str] = None, template_repo=Depends(get_repository(ResourceTemplateRepository))) -> WorkspaceTemplateInResponse:
    template = await get_template(workspace_template_name, template_repo, ResourceType.Workspace, is_update=is_update, version=version)
    return TypeAdapter(WorkspaceTemplateInResponse).validate_python(template)
