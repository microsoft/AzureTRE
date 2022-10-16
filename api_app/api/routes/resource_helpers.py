from datetime import datetime
import logging
from copy import deepcopy
from typing import Dict, Any

from fastapi import HTTPException
from starlette import status
from db.repositories.resources import ResourceRepository
from models.domain.resource_template import ResourceTemplate
from models.domain.authentication import User

from db.errors import DuplicateEntity, EntityDoesNotExist
from db.repositories.operations import OperationRepository
from db.repositories.resource_templates import ResourceTemplateRepository
from models.domain.resource import ResourceType, Resource
from models.domain.operation import Operation
from resources import strings
from service_bus.resource_request_sender import send_resource_request_message, RequestAction
from services.authentication import get_access_service


async def save_and_deploy_resource(resource: Resource, resource_repo: ResourceRepository, operations_repo: OperationRepository, resource_template_repo: ResourceTemplateRepository, user: User, resource_template: ResourceTemplate) -> Operation:
    try:
        resource.user = user
        resource.updatedWhen = get_timestamp()

        # Making a copy to save with secrets masked
        masked_resource = deepcopy(resource)
        masked_resource.properties = mask_sensitive_properties(resource.properties, resource_template)
        resource_repo.save_item(masked_resource)
    except Exception as e:
        logging.error(f'Failed saving resource item {resource.id}: {e}')
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=strings.STATE_STORE_ENDPOINT_NOT_RESPONDING)

    try:
        operation = await send_resource_request_message(
            resource=resource,
            operations_repo=operations_repo,
            resource_repo=resource_repo,
            user=user,
            resource_template=resource_template,
            resource_template_repo=resource_template_repo,
            action=RequestAction.Install)
        return operation
    except Exception as e:
        resource_repo.delete_item(resource.id)
        logging.error(f"Failed send resource request message: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=strings.SERVICE_BUS_GENERAL_ERROR_MESSAGE)


def mask_sensitive_properties(properties: Dict[str, Any], template: ResourceTemplate) -> dict:
    updated_resource_parameters = properties

    for prop_name, prop in template.properties.items():
        if prop.sensitive is True and prop_name in properties:
            updated_resource_parameters = {**properties}
            updated_resource_parameters[prop_name] = strings.REDACTED_SENSITIVE_VALUE
    return updated_resource_parameters


def construct_location_header(operation: Operation) -> str:
    return f'/api{operation.resourcePath}/operations/{operation.id}'


def get_identity_role_assignments(user):
    access_service = get_access_service()
    return access_service.get_identity_role_assignments(user.id)


def get_app_user_roles_assignments_emails(app_obj_id):
    access_service = get_access_service()
    return access_service.get_app_user_role_assignments_emails(app_obj_id)


async def send_uninstall_message(resource: Resource, resource_repo: ResourceRepository, operations_repo: OperationRepository, resource_type: ResourceType, resource_template_repo: ResourceTemplateRepository, user: User, resource_template: ResourceTemplate) -> Operation:
    try:
        operation = await send_resource_request_message(
            resource=resource,
            operations_repo=operations_repo,
            resource_repo=resource_repo,
            user=user,
            resource_template_repo=resource_template_repo,
            resource_template=resource_template,
            action=RequestAction.UnInstall)
        return operation
    except Exception as e:
        logging.error(f"Failed to send {resource_type} resource delete message: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=strings.SERVICE_BUS_GENERAL_ERROR_MESSAGE)


async def send_custom_action_message(resource: Resource, resource_repo: ResourceRepository, custom_action: str, resource_type: ResourceType, operations_repo: OperationRepository, resource_template_repo: ResourceTemplateRepository, user: User, parent_service_name: str = None) -> Operation:

    # Validate that the custom_action specified is present in the resource template
    resource_template = resource_template_repo.get_template_by_name_and_version(resource.templateName, resource.templateVersion, resource_type, parent_service_name=parent_service_name)
    if not resource_template.customActions:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=strings.CUSTOM_ACTIONS_DO_NOT_EXIST)
    elif not any(action.name == custom_action for action in resource_template.customActions):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=strings.CUSTOM_ACTION_NOT_DEFINED)

    try:
        operation = await send_resource_request_message(
            resource=resource,
            operations_repo=operations_repo,
            resource_repo=resource_repo,
            user=user,
            resource_template=resource_template,
            resource_template_repo=resource_template_repo,
            action=custom_action)
        return operation
    except Exception as e:
        logging.error(f"Failed to send {resource_type} resource custom action message: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=strings.SERVICE_BUS_GENERAL_ERROR_MESSAGE)


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


def get_timestamp() -> float:
    return datetime.utcnow().timestamp()
