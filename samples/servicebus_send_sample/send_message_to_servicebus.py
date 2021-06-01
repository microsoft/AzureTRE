from azure.servicebus import ServiceBusClient, ServiceBusMessage


CONNECTION_STR = ""
QUEUE_NAME = "workspacequeue"


def send_single_message(sender, data):
    message = ServiceBusMessage(data)
    sender.send_messages(message)
    print(f"Sent: {data}")


def main():
    with open('createWorkspace.json', 'r') as file:
        data = file.read().replace('\n', '')

    servicebus_client = ServiceBusClient.from_connection_string(conn_str=CONNECTION_STR, logging_enable=True)

    with servicebus_client:
        sender = servicebus_client.get_queue_sender(queue_name=QUEUE_NAME)
        with sender:
            send_single_message(sender, data)


if __name__ == "__main__":
    main()
