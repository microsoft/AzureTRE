import json
from azure.identity.aio import DefaultAzureCredential
from azure.servicebus import ServiceBusMessage
from azure.servicebus.aio import ServiceBusClient

from core import config
from models.domain.resource import Resource


class ServiceBus:
    """
    Implements methods to operate the service bus in the core infrastructure of Azure TRE.
    """
    @staticmethod
    def _create_request_message(resource: Resource) -> str:
        return json.dumps({
            "action": "install",
            "name": resource.resourceTemplateName,
            "version": resource.resourceTemplateVersion,
            "parameters": resource.resourceTemplateParameters
        })

    async def send_resource_request_message(self, resource: Resource):
        """
        Sends a resource request message for the resource to the service bus
        :param resource: resource to deploy
        """
        resource_request_message = self._create_request_message(resource)

        credential = DefaultAzureCredential()
        service_bus_client = ServiceBusClient(config.SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE, credential)

        async with service_bus_client:
            sender = service_bus_client.get_queue_sender(queue_name=config.SERVICE_BUS_RESOURCE_REQUEST_QUEUE)

            async with sender:
                await sender.send_messages(ServiceBusMessage(resource_request_message))

        await credential.close()
