import logging
import json

import azure.functions as func
from azure.storage.blob import BlobServiceClient

from shared_code import blob_operations


def delete_blob_and_container_if_last_blob(blob_url: str):
    storage_account_name, container_name, blob_name = blob_operations.get_blob_info_from_blob_url(blob_url=blob_url)
    credential = blob_operations.get_credential()
    blob_service_client = BlobServiceClient(
        account_url=blob_operations.get_account_url(storage_account_name),
        credential=credential)
    container_client = blob_service_client.get_container_client(container_name)

    if not blob_name:
        logging.info(f'No specific blob specified, deleting the entire container: {container_name}')
        container_client.delete_container()
        return

    # If it's the only blob in the container, we need to delete the container too
    # Check how many blobs are in the container (note: this exhausts the generator)
    blobs_num = sum(1 for _ in container_client.list_blobs())
    logging.info(f'Found {blobs_num} blobs in the container')

    # Deleting blob
    logging.info(f'Deleting blob {blob_name}...')
    blob_client = container_client.get_blob_client(blob_name)
    blob_client.delete_blob()

    if blobs_num == 1:
        # Need to delete the container too
        logging.info(f'There was one blob in the container. Deleting container {container_name}...')
        container_client.delete_container()


def main(msg: func.ServiceBusMessage):
    body = msg.get_body().decode('utf-8')
    logging.info(f'Python ServiceBus queue trigger processed message: {body}')
    json_body = json.loads(body)

    blob_url = json_body["data"]["blob_to_delete"]
    logging.info(f'Blob to delete is {blob_url}')

    delete_blob_and_container_if_last_blob(blob_url)
