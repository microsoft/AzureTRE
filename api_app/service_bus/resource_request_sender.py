import json
import logging

from azure.identity.aio import DefaultAzureCredential
from azure.servicebus import ServiceBusMessage
from azure.servicebus.aio import ServiceBusClient
from contextlib import asynccontextmanager
from db.repositories.resources import ResourceRepository
from db.repositories.resource_templates import ResourceTemplateRepository
from service_bus.step_helpers import update_resource_for_step
from models.domain.resource_template import ResourceTemplate

from models.domain.authentication import User

from core import config
from resources import strings

from models.domain.request_action import RequestAction
from models.domain.resource import Resource
from models.domain.operation import Status, Operation

from db.repositories.operations import OperationRepository


async def send_resource_request_message(resource: Resource, operations_repo: OperationRepository, resource_repo: ResourceRepository, user: User, resource_template: ResourceTemplate, resource_template_repo: ResourceTemplateRepository, action: RequestAction = RequestAction.Install) -> Operation:
    """
    Creates and sends a resource request message for the resource to the Service Bus.
    The resource ID is added to the message to serve as an correlation ID for the deployment process.

    :param resource: The resource to deploy.
    :param action: install, uninstall etc.
    """

    status = Status.InvokingAction
    message = strings.RESOURCE_ACTION_STATUS_INVOKING

    if action == RequestAction.Install:
        status = Status.NotDeployed
        message = strings.RESOURCE_STATUS_NOT_DEPLOYED_MESSAGE
    elif action == RequestAction.UnInstall:
        status = Status.Deleting
        message = strings.RESOURCE_STATUS_DELETING
    elif action == RequestAction.Upgrade:
        status = Status.NotDeployed
        message = strings.RESOURCE_STATUS_UPGRADE_NOT_STARTED_MESSAGE

    # add the operation to the db - this will create all the steps needed (if any are defined in the template)
    operation = operations_repo.create_operation_item(resource_id=resource.id, status=status, action=action, message=message, resource_path=resource.resourcePath, user=user, resource_template=resource_template)

    resource_to_send = resource
    step_id = "main"

    # get the first step - if it's not "main" - get the resource, patch it, return it
    if resource_template.pipeline is not None:
        if action in resource_template.pipeline:
            first_step = resource_template.pipeline[action].steps[0]
            if first_step["stepId"] != "main":
                step_id = first_step["stepId"]
                resource_to_send = update_resource_for_step(
                    template_step=first_step,
                    resource_repo=resource_repo,
                    resource_template_repo=resource_template_repo,
                    resource_template=resource_template,
                    user=user)

    content = json.dumps(resource_to_send.get_resource_request_message_payload(operation_id=operation.id, step_id=step_id, action=action))

    resource_request_message = ServiceBusMessage(body=content, correlation_id=operation.id, session_id=resource.id)
    logging.info(f"Sending resource request message with correlation ID {resource_request_message.correlation_id}, action: {action}")
    await _send_message(resource_request_message, config.SERVICE_BUS_RESOURCE_REQUEST_QUEUE)
    return operation


@asynccontextmanager
async def _get_default_credentials():
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
    async with _get_default_credentials() as credential:
        service_bus_client = ServiceBusClient(config.SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE, credential)

        async with service_bus_client:
            sender = service_bus_client.get_queue_sender(queue_name=queue)

            async with sender:
                await sender.send_messages(message)
