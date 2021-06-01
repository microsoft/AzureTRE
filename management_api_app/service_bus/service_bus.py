from azure.identity import DefaultAzureCredential
from azure.servicebus import ServiceBusClient, ServiceBusMessage
from core import config

class ServiceBus():
    """
    Implements methods to operate the service bus in the core infrastructure of Azure TRE.
    """

    async def send_resource_request_message(self, resource_request_message: str):
        """
        Sends the given message to the resource request queue.

        :param resource_request_message: The message to send.
        :type resource_request_message: str
        """
        credential = DefaultAzureCredential()
        service_bus_client = ServiceBusClient(config.SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE, credential)

        async with service_bus_client:
            sender = service_bus_client.get_queue_sender(queue_name=config.SERVICE_BUS_RESOURCE_REQUEST_QUEUE)

            async with sender:
                await sender.send_messages(ServiceBusMessage(resource_request_message))

        await credential.close()
