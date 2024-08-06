from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import parse_obj_as

from api.helpers import get_repository
from db.errors import EntityDoesNotExist, EntityVersionExist, InvalidInput
from db.repositories.resource_templates import ResourceTemplateRepository
from models.domain.resource import ResourceType
from models.schemas.resource_template import ResourceTemplateInResponse, ResourceTemplateInformationInList
from models.schemas.shared_service_template import SharedServiceTemplateInCreate, SharedServiceTemplateInResponse
from resources import strings
from services.authentication import get_current_admin_user, get_current_tre_user_or_tre_admin
from api.routes.resource_helpers import get_template


shared_service_templates_core_router = APIRouter(dependencies=[Depends(get_current_tre_user_or_tre_admin)])


@shared_service_templates_core_router.get("/shared-service-templates", response_model=ResourceTemplateInformationInList, name=strings.API_GET_SHARED_SERVICE_TEMPLATES)
async def get_shared_service_templates(authorized_only: bool = False, template_repo=Depends(get_repository(ResourceTemplateRepository)), user=Depends(get_current_tre_user_or_tre_admin)) -> ResourceTemplateInformationInList:
    templates_infos = await template_repo.get_templates_information(ResourceType.SharedService, user.roles if authorized_only else None)
    return ResourceTemplateInformationInList(templates=templates_infos)


@shared_service_templates_core_router.get("/shared-service-templates/{shared_service_template_name}", response_model=SharedServiceTemplateInResponse, response_model_exclude_none=True, name=strings.API_GET_SHARED_SERVICE_TEMPLATE_BY_NAME, dependencies=[Depends(get_current_tre_user_or_tre_admin)])
async def get_shared_service_template(shared_service_template_name: str, is_update: bool = False, version: Optional[str] = None, template_repo=Depends(get_repository(ResourceTemplateRepository))) -> SharedServiceTemplateInResponse:
    try:
        template = await get_template(shared_service_template_name, template_repo, ResourceType.SharedService, is_update=is_update, version=version)
        return parse_obj_as(SharedServiceTemplateInResponse, template)
    except EntityDoesNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=strings.SHARED_SERVICE_TEMPLATE_DOES_NOT_EXIST)


@shared_service_templates_core_router.post("/shared-service-templates", status_code=status.HTTP_201_CREATED, response_model=SharedServiceTemplateInResponse, response_model_exclude_none=True, name=strings.API_CREATE_SHARED_SERVICE_TEMPLATES, dependencies=[Depends(get_current_admin_user)])
async def register_shared_service_template(template_input: SharedServiceTemplateInCreate, template_repo=Depends(get_repository(ResourceTemplateRepository))) -> ResourceTemplateInResponse:
    try:
        return await template_repo.create_and_validate_template(template_input, ResourceType.SharedService)
    except EntityVersionExist:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=strings.SHARED_SERVICE_TEMPLATE_VERSION_EXISTS)
    except InvalidInput as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
