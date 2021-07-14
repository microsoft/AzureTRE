import json
import logging
from azure.identity.aio import DefaultAzureCredential
from azure.servicebus import ServiceBusMessage
from azure.servicebus.aio import ServiceBusClient
from contextlib import asynccontextmanager

from core import config
from models.domain.resource import Resource


async def send_resource_request_message(resource: Resource):
    """
    Creates and sends a resource request message for the resource to the Service Bus.
    The resource ID is added to the message to serve as an correlation ID for the deployment process.

    :param resource: The resource to deploy.
    :type resource: Resource
    """
    content = json.dumps({
        "action": "install",
        "id": resource.id,
        "name": resource.resourceTemplateName,
        "version": resource.resourceTemplateVersion,
        "parameters": resource.resourceTemplateParameters
    })

    resource_request_message = ServiceBusMessage(body=content, correlation_id=resource.id)
    logging.info(f"Sending resource request message with correlation ID {resource_request_message.correlation_id}")
    await _send_message(resource_request_message, config.SERVICE_BUS_RESOURCE_REQUEST_QUEUE)


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
