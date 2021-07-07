import os
import uuid

from azure.servicebus import ServiceBusClient, ServiceBusMessage


CREATE_WORKSPACE_REQUEST_DATA_FILE = "createWorkspaceRequestData.json"


def send_service_bus_message(service_bus_connection_string, service_bus_queue_name, correlation_id):
    with open(CREATE_WORKSPACE_REQUEST_DATA_FILE, "r") as file:
        data = file.read().replace('\n', '')

    service_bus_client = ServiceBusClient.from_connection_string(
        conn_str=service_bus_connection_string, logging_enable=True)

    with service_bus_client:
        queue_sender = service_bus_client.get_queue_sender(queue_name=service_bus_queue_name)

        with queue_sender:
            message = ServiceBusMessage(body=data, correlation_id=correlation_id)
            queue_sender.send_messages(message)
            print(f"Service Bus message sent to queue: {data}")


if __name__ == "__main__":
    try:
        service_bus_connection_string = os.environ["SERVICE_BUS_CONNECTION_STRING"]
        resource_request_queue_name = os.environ["SERVICE_BUS_RESOURCE_REQUEST_QUEUE"]
        correlation_id = str(uuid.uuid4())

        print(f"Service Bus queue name: {resource_request_queue_name}")
        print(f"Generated correlation ID: {correlation_id}")

        send_service_bus_message(service_bus_connection_string, resource_request_queue_name, correlation_id)
    except Exception as e:
        print(f"Failed to send a Service Bus message: {type(e).__name__}: {e}")
