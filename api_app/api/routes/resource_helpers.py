from datetime import datetime
import logging
from copy import deepcopy
from typing import Dict, Any

from fastapi import HTTPException, status
from db.repositories.resources import ResourceRepository
from models.domain.resource_template import ResourceTemplate
from models.domain.authentication import User

from db.errors import DuplicateEntity, EntityDoesNotExist
from db.repositories.operations import OperationRepository
from db.repositories.resource_templates import ResourceTemplateRepository
from models.domain.resource import ResourceType, Resource
from models.domain.operation import Operation
from resources import strings
from service_bus.resource_request_sender import (
    send_resource_request_message,
    RequestAction,
)
from services.authentication import get_access_service


async def save_and_deploy_resource(
    resource: Resource,
    resource_repo: ResourceRepository,
    operations_repo: OperationRepository,
    resource_template_repo: ResourceTemplateRepository,
    user: User,
    resource_template: ResourceTemplate,
) -> Operation:
    try:
        resource.user = user
        resource.updatedWhen = get_timestamp()

        # Making a copy to save with secrets masked
        masked_resource = deepcopy(resource)
        masked_resource.properties = mask_sensitive_properties(
            resource.properties, resource_template
        )
        await resource_repo.save_item(masked_resource)
    except Exception:
        logging.exception(f"Failed saving resource item {resource.id}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=strings.STATE_STORE_ENDPOINT_NOT_RESPONDING,
        )

    try:
        operation = await send_resource_request_message(
            resource=resource,
            operations_repo=operations_repo,
            resource_repo=resource_repo,
            user=user,
            resource_template=resource_template,
            resource_template_repo=resource_template_repo,
            action=RequestAction.Install,
        )
        return operation
    except Exception:
        await resource_repo.delete_item(resource.id)
        logging.exception("Failed send resource request message")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=strings.SERVICE_BUS_GENERAL_ERROR_MESSAGE,
        )


def mask_sensitive_properties(
    properties: Dict[str, Any], template: ResourceTemplate
) -> dict:
    updated_resource_parameters = deepcopy(properties)

    flattened_template_props = {}

    # recusrse the template and flatten all properties into a list
    def flatten_template_props(template_fragment: dict):
        if template_fragment is None:
            return

        for prop_name, prop in template_fragment.items():
            if prop_name == "pipeline":
                continue

            if (
                prop_name == "properties"
                and template_fragment["properties"] is not None
            ):
                for inner_prop_name, inner_prop in template_fragment[
                    "properties"
                ].items():
                    flattened_template_props[inner_prop_name] = inner_prop

            if isinstance(prop, list) and len(prop) > 0:
                for p in prop:
                    if isinstance(p, dict):
                        flatten_template_props(p)

            if isinstance(prop, dict) and prop_name != "if":
                flatten_template_props(prop)

    flatten_template_props(template.dict())

    def recurse_input_props(prop_dict: dict):
        for prop_name, prop in prop_dict.items():
            if (
                prop_name in flattened_template_props
                and "sensitive" in flattened_template_props[prop_name]
                and flattened_template_props[prop_name]["sensitive"] is True
            ):
                prop_dict[prop_name] = strings.REDACTED_SENSITIVE_VALUE
            if isinstance(prop, dict):
                recurse_input_props(prop)

    recurse_input_props(updated_resource_parameters)

    return updated_resource_parameters


def construct_location_header(operation: Operation) -> str:
    return f"/api{operation.resourcePath}/operations/{operation.id}"


def get_identity_role_assignments(user):
    access_service = get_access_service()
    return access_service.get_identity_role_assignments(user.id)


def get_app_user_roles_assignments_emails(app_obj_id):
    access_service = get_access_service()
    return access_service.get_app_user_role_assignments_emails(app_obj_id)


async def send_uninstall_message(
    resource: Resource,
    resource_repo: ResourceRepository,
    operations_repo: OperationRepository,
    resource_type: ResourceType,
    resource_template_repo: ResourceTemplateRepository,
    user: User,
    resource_template: ResourceTemplate,
) -> Operation:
    try:
        operation = await send_resource_request_message(
            resource=resource,
            operations_repo=operations_repo,
            resource_repo=resource_repo,
            user=user,
            resource_template_repo=resource_template_repo,
            resource_template=resource_template,
            action=RequestAction.UnInstall,
        )
        return operation
    except Exception:
        logging.exception("Failed to send {resource_type} resource delete message")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=strings.SERVICE_BUS_GENERAL_ERROR_MESSAGE,
        )


async def send_custom_action_message(
    resource: Resource,
    resource_repo: ResourceRepository,
    custom_action: str,
    resource_type: ResourceType,
    operations_repo: OperationRepository,
    resource_template_repo: ResourceTemplateRepository,
    user: User,
    parent_service_name: str = None,
) -> Operation:

    # Validate that the custom_action specified is present in the resource template
    resource_template = resource_template_repo.get_template_by_name_and_version(
        resource.templateName,
        resource.templateVersion,
        resource_type,
        parent_service_name=parent_service_name,
    )
    if not resource_template.customActions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=strings.CUSTOM_ACTIONS_DO_NOT_EXIST,
        )
    elif not any(
        action.name == custom_action for action in resource_template.customActions
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=strings.CUSTOM_ACTION_NOT_DEFINED,
        )

    try:
        operation = await send_resource_request_message(
            resource=resource,
            operations_repo=operations_repo,
            resource_repo=resource_repo,
            user=user,
            resource_template=resource_template,
            resource_template_repo=resource_template_repo,
            action=custom_action,
        )
        return operation
    except Exception:
        logging.exception("Failed to send {resource_type} resource custom action message")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=strings.SERVICE_BUS_GENERAL_ERROR_MESSAGE,
        )


async def get_template(
    template_name: str,
    template_repo: ResourceTemplateRepository,
    resource_type: ResourceType,
    parent_service_template_name: str = "",
    is_update: bool = False,
    version: str = None,
) -> dict:
    try:
        template = (
            await template_repo.get_template_by_name_and_version(
                template_name, version, resource_type, parent_service_template_name
            )
            if version
            else await template_repo.get_current_template(
                template_name, resource_type, parent_service_template_name
            )
        )

        return template_repo.enrich_template(template, is_update=is_update)
    except EntityDoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=strings.TEMPLATE_DOES_NOT_EXIST,
        )
    except DuplicateEntity:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=strings.NO_UNIQUE_CURRENT_FOR_TEMPLATE,
        )
    except Exception as e:
        logging.debug(e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=strings.STATE_STORE_ENDPOINT_NOT_RESPONDING,
        )


def get_timestamp() -> float:
    return datetime.utcnow().timestamp()
