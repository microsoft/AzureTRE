import json
import os
from azure.servicebus import ServiceBusClient, ServiceBusMessage, ServiceBusReceiver, ServiceBusReceivedMessage, AutoLockRenewer


class ServiceBus:
    """
    Implements methods to operate the service bus in the core infrastructure of Azure TRE.
    """

    def __init__(self):
        service_bus_client = ServiceBusClient.from_connection_string(conn_str=os.environ["SERVICE_BUS_CONNECTION_STRING"])
        self.sender = service_bus_client.get_queue_sender(queue_name=os.environ["SERVICE_BUS_DEPLOYMENT_STATUS_UPDATE_QUEUE"])
        self.resource_request_queue_receiver = service_bus_client.get_queue_receiver(os.environ["SERVICE_BUS_RESOURCE_REQUEST_QUEUE"], recieve_mode="PEEK_LOCK")

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

        self.sender.send_messages(ServiceBusMessage(body=resource_request_message, correlation_id=id))

    def get_resource_job_queue_message(self) -> ServiceBusReceiver:
        # wait for message
        msg = self.resource_request_queue_receiver.receive_messages(max_message_count=1, max_wait_time=None)[0]

        # renew lock for 1800 seconds - 30 mins - max length of job execution
        renewer = AutoLockRenewer()
        renewer.register(self.resource_request_queue_receiver, msg, max_lock_renewal_duration=800)

        return msg

    def complete_resource_job_queue_message(self, msg: ServiceBusReceivedMessage):
        self.resource_request_queue_receiver.complete_message(msg)
