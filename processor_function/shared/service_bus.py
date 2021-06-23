import json
import os
from azure.servicebus import ServiceBusClient, ServiceBusMessage


class ServiceBus:
    """
    Implements methods to operate the service bus in the core infrastructure of Azure TRE.
    """

    def send_status_update_message(self, id: str, status: str, message: str):
        """
        Sends a resource request message for the resource to the service bus
        :param resource: resource to deploy
        """
        resource_request_message = json.dumps({
            "id": id,
            "status": status,
            "message": message
        })

        service_bus_client = ServiceBusClient.from_connection_string(conn_str=os.environ["SERVICE_BUS_CONNECTION_STRING"])

        with service_bus_client:
            sender = service_bus_client.get_queue_sender(queue_name=os.environ["SERVICE_BUS_DEPLOYMENT_STATUS_UPDATE_QUEUE"])

            with sender:
                sender.send_messages(ServiceBusMessage(body=resource_request_message, correlation_id=id))
