from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import TypeAdapter

from api.routes.resource_helpers import get_template
from db.errors import EntityVersionExist, InvalidInput
from api.helpers import get_repository
from db.repositories.resource_templates import ResourceTemplateRepository
from models.domain.resource import ResourceType
from models.schemas.resource_template import ResourceTemplateInResponse, ResourceTemplateInformationInList
from models.schemas.workspace_service_template import WorkspaceServiceTemplateInCreate, WorkspaceServiceTemplateInResponse
from resources import strings
from services.authentication import get_current_admin_user, get_current_tre_user_or_tre_admin


workspace_service_templates_core_router = APIRouter(dependencies=[Depends(get_current_tre_user_or_tre_admin)])


@workspace_service_templates_core_router.get("/workspace-service-templates", response_model=ResourceTemplateInformationInList, name=strings.API_GET_WORKSPACE_SERVICE_TEMPLATES, dependencies=[Depends(get_current_tre_user_or_tre_admin)])
async def get_workspace_service_templates(template_repo=Depends(get_repository(ResourceTemplateRepository))) -> ResourceTemplateInformationInList:
    templates_infos = await template_repo.get_templates_information(ResourceType.WorkspaceService)
    return ResourceTemplateInformationInList(templates=templates_infos)


@workspace_service_templates_core_router.get("/workspace-service-templates/{service_template_name}", response_model=WorkspaceServiceTemplateInResponse, response_model_exclude_none=True, name=strings.API_GET_WORKSPACE_SERVICE_TEMPLATE_BY_NAME, dependencies=[Depends(get_current_tre_user_or_tre_admin)])
async def get_workspace_service_template(service_template_name: str, is_update: bool = False, version: Optional[str] = None, template_repo=Depends(get_repository(ResourceTemplateRepository))) -> WorkspaceServiceTemplateInResponse:
    template = await get_template(service_template_name, template_repo, ResourceType.WorkspaceService, is_update=is_update, version=version)
    return TypeAdapter(WorkspaceServiceTemplateInResponse).validate_python(template)
