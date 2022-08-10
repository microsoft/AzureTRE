import logging

import azure.functions as func
import json

from shared_code import blob_operations
from pydantic import BaseModel, parse_obj_as


class ToDeleteProperties(BaseModel):
    account_rg: str
    account_name: str
    request_id: str


def main(msg: func.ServiceBusMessage):
    body = msg.get_body().decode('utf-8')
    logging.info(f'Python ServiceBus queue trigger processed mesage: {body}')

    storage_client = blob_operations.get_storage_management_client()

    json_body = json.loads(body)
    blob_url = json_body["blob_to_delete"]
    logging.info(f'Deleting the blob {blob_url} (not actually deleting yet)')

    # TODO: this doesn't support / in blob name. Are we going to have blobs like this?
    # Maybe there are directories?
    blob_client = BlobClient.from_blob_url(blob_url)

    # Checking permissions for now
    logging.info(f'Blob properties: {blob_client.get_blob_properties()}'

    # blob_client.delete_blob()
    # Example of URL: "https://stalimextanyademo.blob.core.windows.net/c144728c-3c69-4a58-afec-48c2ec8bfd45/test_dataset.txt"

    # If it's the only blob in the container, we need to delete the container too
    # Check how many blobs are in the container
    storage_account_name, container_name = re.search(r'https://(.*?).blob.core.windows.net/(.*?)/', blob_url).groups()

    source_blob_service_client = BlobServiceClient(account_url=f"https://{storage_account_name}.blob.core.windows.net/",
                                                   credential=blob_operations.get_credential())
    source_container_client = source_blob_service_client.get_container_client(container_name)

    for blob in source_container_client.list_blobs():
        logging.info(f'found blob {blob.name}')
