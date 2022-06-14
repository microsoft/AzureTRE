from azure.identity.aio import DefaultAzureCredential
from azure.servicebus import ServiceBusMessage
from azure.servicebus.aio import ServiceBusClient
from contextlib import asynccontextmanager

from pydantic import parse_obj_as
from models.domain.resource_template import PipelineStep
from models.domain.operation import OperationStep
from models.domain.resource import Resource, ResourceType
from db.repositories.resource_templates import ResourceTemplateRepository
from models.domain.authentication import User
from models.schemas.resource import ResourcePatch
from db.repositories.resources import ResourceRepository
from core import config
import logging
from azure.cosmos.exceptions import CosmosAccessConditionFailedError


@asynccontextmanager
async def default_credentials():
    """
    Yields the default credentials.
    """
    credential = DefaultAzureCredential(managed_identity_client_id=config.MANAGED_IDENTITY_CLIENT_ID)
    yield credential
    await credential.close()


async def _send_message(message: ServiceBusMessage, queue: str):
    """
    Sends the given message to the given queue in the Service Bus.

    :param message: The message to send.
    :type message: ServiceBusMessage
    :param queue: The Service Bus queue to send the message to.
    :type queue: str
    """
    async with default_credentials() as credential:
        service_bus_client = ServiceBusClient(config.SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE, credential)

        async with service_bus_client:
            sender = service_bus_client.get_queue_sender(queue_name=queue)

            async with sender:
                await sender.send_messages(message)


async def send_deployment_message(content, correlation_id, session_id, action):
    resource_request_message = ServiceBusMessage(body=content, correlation_id=correlation_id, session_id=session_id)
    logging.info(f"Sending resource request message with correlation ID {resource_request_message.correlation_id}, action: {action}")
    await _send_message(resource_request_message, config.SERVICE_BUS_RESOURCE_REQUEST_QUEUE)


def update_resource_for_step(
    operation_step: OperationStep,
    resource_repo: ResourceRepository,
    resource_template_repo: ResourceTemplateRepository,
    primary_resource_id: str,
    resource_to_update_id: str,
    primary_action: str,
    user: User) -> Resource:

    # get primary resource to use in substitutions
    primary_resource = resource_repo.get_resource_by_id(primary_resource_id)

    # get secondary resource to be updated
    resource_to_update = resource_repo.get_resource_by_id(resource_to_update_id)

    # if this is main, just leave it alone and return it
    if operation_step.stepId == "main":
        return primary_resource

    # get the template for the primary resource, to get all the step details for substitutions
    primary_parent_service_name = ""
    if primary_resource.resourceType == ResourceType.UserResource:
        primary_parent_workspace_service = resource_repo.get_resource_by_id(primary_resource.parentWorkspaceServiceId)
        primary_parent_service_name = primary_parent_workspace_service.templateName
    primary_template = resource_template_repo.get_current_template(primary_resource.templateName, primary_resource.resourceType, primary_parent_service_name)

    # get the template step
    template_step = None
    for step in primary_template.pipeline.dict()[primary_action]:
        if step["stepId"] == operation_step.stepId:
            template_step = parse_obj_as(PipelineStep, step)
            break

    if template_step is None:
        raise f"Cannot find step with id of {operation_step.stepId} in template {primary_resource.templateName} for action {primary_action}"

    # substitute values into new property bag for update
    properties = substitute_properties(template_step, primary_resource)

    if template_step.resourceAction == "upgrade":
        resource_to_send = try_upgrade_with_retries(
            num_retries=3,
            attempt_count=0,
            resource_repo=resource_repo,
            resource_template_repo=resource_template_repo,
            properties=properties,
            user=user,
            resource_to_update_id=resource_to_update_id
        )

        return resource_to_send

    else:
        raise Exception("Only upgrade is currently supported for pipeline steps")


def substitute_properties(template_step: PipelineStep, primary_resource: Resource) -> dict:
    properties = {}
    for prop in template_step.properties:
        val = prop.value
        if isinstance(prop.value, dict):
            val = recurse_object(prop.value, primary_resource.dict())
        else:
            val = substitute_value(val, primary_resource.dict())
        properties[prop.name] = val

    return properties


def recurse_object(obj: dict, primary_resource_dict: dict) -> dict:
    for prop in obj:
        if isinstance(obj[prop], list):
            for i in range(0, len(obj[prop])):
                obj[prop][i] = recurse_object(obj[prop][i], primary_resource_dict)
        if isinstance(obj[prop], dict):
            obj[prop] = recurse_object(obj[prop])
        else:
            obj[prop] = substitute_value(obj[prop], primary_resource_dict)

    return obj


def substitute_value(val: str, primary_resource_dict: dict):
    if "{{" not in val:
        return val

    val = val.replace("{{ ", "{{").replace(" }}", "}}")

    # if the value being substituted in is a simple type, we can return it in the string, to allow for concatenation
    # like "This was deployed by {{ resource.id }}"
    # else if the value being injected in is a dict/list - we shouldn't try to concatenate that, we'll return the true value and drop any surrounding text

    # extract the tokens to replace
    tokens = []
    parts = val.split("{{")
    for p in parts:
        if len(p) > 0 and "}}" in p:
            t = p[0:p.index("}}")]
            tokens.append(t)

    for t in tokens:
        # t = "resource.properties.prop_1"
        p = t.split(".")
        if p[0] == "resource":
            prop_to_get = primary_resource_dict
            for i in range(1, len(p)):
                prop_to_get = prop_to_get[p[i]]

            # if the value to inject is actually an object / list - just return it, else replace the value in the string
            if isinstance(prop_to_get, dict) or isinstance(prop_to_get, list):
                return prop_to_get
            else:
                val = val.replace("{{" + t + "}}", str(prop_to_get))

    return val


def try_upgrade_with_retries(num_retries: int, attempt_count: int, resource_repo: ResourceRepository, resource_template_repo: ResourceTemplateRepository, properties: dict, user: User, resource_to_update_id: str) -> Resource:
    try:
        return try_upgrade(
            resource_repo=resource_repo,
            resource_template_repo=resource_template_repo,
            properties=properties,
            user=user,
            resource_to_update_id=resource_to_update_id
        )
    except CosmosAccessConditionFailedError as e:
        logging.warn(f"Etag mismatch for {resource_to_update_id}. Retrying.")
        if attempt_count < num_retries:
            try_upgrade_with_retries(
                num_retries=num_retries,
                attempt_count=(attempt_count + 1),
                resource_repo=resource_repo,
                resource_template_repo=resource_template_repo,
                properties=properties,
                user=user,
                resource_to_update_id=resource_to_update_id
            )
        else:
            raise e


def try_upgrade(resource_repo: ResourceRepository, resource_template_repo: ResourceTemplateRepository, properties: dict, user: User, resource_to_update_id: str) -> Resource:
    resource_to_update = resource_repo.get_resource_by_id(resource_to_update_id)

    # get the template for the resource to upgrade
    parent_service_name = ""
    if resource_to_update.resourceType == ResourceType.UserResource:
        parent_service_name = resource_to_update["parentWorkspaceServiceId"]

    resource_template_to_send = resource_template_repo.get_current_template(resource_to_update.templateName, resource_to_update.resourceType, parent_service_name)

    # create the patch
    patch = ResourcePatch(
        properties=properties
    )

    # validate and submit the patch
    resource_to_send, _ = resource_repo.patch_resource(
        resource=resource_to_update,
        resource_patch=patch,
        resource_template=resource_template_to_send,
        etag=resource_to_update.etag,
        resource_template_repo=resource_template_repo,
        user=user)

    return resource_to_send
