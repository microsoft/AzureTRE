from fastapi import Depends, HTTPException, Path, status

from api.helpers import get_repository
from db.errors import EntityDoesNotExist
from db.repositories.resource_templates import ResourceTemplateRepository
from models.domain.resource import ResourceType
from models.domain.resource_template import ResourceTemplate
from resources import strings


async def get_workspace_service_template_by_name_from_path(service_template_name: str = Path(...), template_repo=Depends(get_repository(ResourceTemplateRepository))) -> ResourceTemplate:
    try:
        return await template_repo.get_current_template(service_template_name, ResourceType.WorkspaceService)
    except EntityDoesNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=strings.WORKSPACE_SERVICE_TEMPLATE_DOES_NOT_EXIST)
