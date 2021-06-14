import json
import logging
from json import JSONDecodeError

from azure.servicebus.aio import ServiceBusClient
from azure.identity.aio import DefaultAzureCredential

from core import config
from resources import strings


async def receive_message_and_update_deployment() -> None:
    """
    Receives message from deployment status update queue and updates the status for
    a Resource in the state stroe.
    """
    credential = DefaultAzureCredential(managed_identity_client_id=config.MANAGED_IDENTITY_CLIENT_ID)
    service_bus_client = ServiceBusClient(config.SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE, credential)

    async with service_bus_client:
        receiver = service_bus_client.get_queue_receiver(queue_name=config.SERVICE_BUS_DEPLOYMENT_STATUS_UPDATE_QUEUE)
        async with receiver:
            received_msgs = await receiver.receive_messages(max_message_count=10, max_wait_time=5)
            for msg in received_msgs:
                try:
                    message = json.loads(str(msg))
                    print(message)
                except JSONDecodeError:
                    logging.error(strings.DEPLOYMENT_STATUS_MESSAGE_FORMAT_INCORRECT)
                await receiver.complete_message(msg)
        await credential.close()
