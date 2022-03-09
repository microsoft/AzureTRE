import logging

from fastapi import HTTPException
from starlette import status

from db.errors import DuplicateEntity, EntityDoesNotExist
from db.repositories.resource_templates import ResourceTemplateRepository
from models.domain.resource import ResourceType
from resources import strings


def get_current_template_by_name(template_name: str, template_repo: ResourceTemplateRepository, resource_type: ResourceType, parent_service_template_name: str = "", is_update: bool = False) -> dict:
    try:
        template = template_repo.get_current_template(template_name, resource_type, parent_service_template_name)
        return template_repo.enrich_template(template, is_update=is_update)
    except EntityDoesNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=strings.TEMPLATE_DOES_NOT_EXIST)
    except DuplicateEntity:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=strings.NO_UNIQUE_CURRENT_FOR_TEMPLATE)
    except Exception as e:
        logging.debug(e)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=strings.STATE_STORE_ENDPOINT_NOT_RESPONDING)
