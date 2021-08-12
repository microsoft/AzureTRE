from fastapi import Depends, HTTPException, Path
from starlette.status import HTTP_404_NOT_FOUND

from db.errors import EntityDoesNotExist
from api.dependencies.database import get_repository
from db.repositories.user_resource_templates import UserResourceTemplateRepository
from models.domain.resource import ResourceType
from models.domain.resource_template import ResourceTemplate
from resources import strings


async def get_workspace_service_template_by_name_from_path(template_name: str = Path(...),
                                                           resource_templates_repo: UserResourceTemplateRepository = Depends(
                                                               get_repository(
                                                                   UserResourceTemplateRepository))) -> ResourceTemplate:
    try:
        return resource_templates_repo.get_current_resource_template_by_name(template_name,
                                                                             ResourceType.WorkspaceService)
    except EntityDoesNotExist:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=strings.TEMPLATE_DOES_NOT_EXIST)
