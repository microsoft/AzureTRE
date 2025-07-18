
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import TypeAdapter

from api.dependencies.workspace_service_templates import get_workspace_service_template_by_name_from_path
from api.routes.resource_helpers import get_template
from db.errors import EntityVersionExist, InvalidInput
from api.helpers import get_repository
from db.repositories.resource_templates import ResourceTemplateRepository
from models.domain.resource import ResourceType
from models.schemas.user_resource_template import UserResourceTemplateInResponse, UserResourceTemplateInCreate
from models.schemas.resource_template import ResourceTemplateInformationInList
from resources import strings
from services.authentication import get_current_admin_user, get_current_tre_user_or_tre_admin


user_resource_templates_core_router = APIRouter(dependencies=[Depends(get_current_tre_user_or_tre_admin)])


@user_resource_templates_core_router.get("/workspace-service-templates/{service_template_name}/user-resource-templates", response_model=ResourceTemplateInformationInList, name=strings.API_GET_USER_RESOURCE_TEMPLATES, dependencies=[Depends(get_current_tre_user_or_tre_admin)])
async def get_user_resource_templates_for_service_template(service_template_name: str, template_repo=Depends(get_repository(ResourceTemplateRepository))) -> ResourceTemplateInformationInList:
    template_infos = await template_repo.get_templates_information(ResourceType.UserResource, parent_service_name=service_template_name)
    return ResourceTemplateInformationInList(templates=template_infos)


@user_resource_templates_core_router.get("/workspace-service-templates/{service_template_name}/user-resource-templates/{user_resource_template_name}", response_model=UserResourceTemplateInResponse, response_model_exclude_none=True, name=strings.API_GET_USER_RESOURCE_TEMPLATE_BY_NAME, dependencies=[Depends(get_current_tre_user_or_tre_admin)])
async def get_user_resource_template(service_template_name: str, user_resource_template_name: str, is_update: bool = False, version: Optional[str] = None, template_repo=Depends(get_repository(ResourceTemplateRepository))) -> UserResourceTemplateInResponse:
    template = await get_template(user_resource_template_name, template_repo, ResourceType.UserResource, service_template_name, is_update=is_update, version=version)
    return TypeAdapter(UserResourceTemplateInResponse).validate_python(template)
