import os
import datetime
import logging
import json
import re

from azure.core.exceptions import ResourceExistsError
from azure.identity import DefaultAzureCredential
from azure.storage.blob import ContainerSasPermissions, generate_container_sas, BlobServiceClient

from exceptions.TooManyFilesInRequestException import TooManyFilesInRequestException
from exceptions.NoFilesInRequestException import NoFilesInRequestException


def get_account_url(account_name: str) -> str:
    return f"https://{account_name}.blob.core.windows.net/"


# TODO: create a blob info dataclass
def get_blob_client_from_blob_info(storage_account_name: str, container_name: str, blob_name: str):
    source_blob_service_client = BlobServiceClient(account_url=f"https://{storage_account_name}.blob.core.windows.net/",
                                                   credential=get_credential())
    source_container_client = source_blob_service_client.get_container_client(container_name)
    return source_container_client.get_blob_client(blob_name)


def create_container(account_name: str, request_id: str):
    try:
        container_name = request_id
        blob_service_client = BlobServiceClient(account_url=get_account_url(account_name),
                                                credential=get_credential())
        blob_service_client.create_container(container_name)
        logging.info(f'Container created for request id: {request_id}.')
    except ResourceExistsError:
        logging.info(f'Did not create a new container. Container already exists for request id: {request_id}.')


def copy_data(source_account_name: str, destination_account_name: str, request_id: str):
    credential = get_credential()
    container_name = request_id

    source_blob_service_client = BlobServiceClient(account_url=get_account_url(source_account_name),
                                                   credential=credential)
    source_container_client = source_blob_service_client.get_container_client(container_name)

    try:
        found_blobs = 0
        blob_name = ""
        for blob in source_container_client.list_blobs():
            if found_blobs > 0:
                msg = "Request with id {} contains more than 1 file. flow aborted.".format(request_id)
                logging.error(msg)
                raise TooManyFilesInRequestException(msg)
            blob_name = blob.name
            found_blobs += 1

        if found_blobs == 0:
            msg = "Request with id {} did not contain any files. flow aborted.".format(request_id)
            logging.error(msg)
            raise NoFilesInRequestException(msg)

    except Exception:
        logging.error('Request with id %s failed.', request_id)
        raise

    udk = source_blob_service_client.get_user_delegation_key(datetime.datetime.utcnow() - datetime.timedelta(hours=1),
                                                             datetime.datetime.utcnow() + datetime.timedelta(hours=1))

    # token geneation with expiry of 1 hour. since its not shared, we can leave it to expire (no need to track/delete)
    # Remove sas token if not needed: https://github.com/microsoft/AzureTRE/issues/2034
    sas_token = generate_container_sas(account_name=source_account_name,
                                       container_name=container_name,
                                       user_delegation_key=udk,
                                       permission=ContainerSasPermissions(read=True),
                                       expiry=datetime.datetime.utcnow() + datetime.timedelta(hours=1))

    source_blob = source_container_client.get_blob_client(blob_name)
    source_url = f'{source_blob.url}?{sas_token}'

    # Set metadata to include the blob url that it is copied from
    metadata = source_blob.get_blob_properties()["metadata"]
    copied_from = json.loads(metadata["copied_from"]) if "copied_from" in metadata else []
    metadata["copied_from"] = json.dumps(copied_from + [source_blob.url])

    # Copy files
    dest_blob_service_client = BlobServiceClient(account_url=get_account_url(destination_account_name),
                                                 credential=credential)
    copied_blob = dest_blob_service_client.get_blob_client(container_name, source_blob.blob_name)
    copy = copied_blob.start_copy_from_url(source_url, metadata=metadata)

    try:
        logging.info("Copy operation returned 'copy_id': '%s', 'copy_status': '%s'", copy["copy_id"],
                     copy["copy_status"])
    except KeyError as e:
        logging.error(f"Failed getting operation id and status {e}")


def get_credential() -> DefaultAzureCredential:
    managed_identity = os.environ.get("MANAGED_IDENTITY_CLIENT_ID")
    if managed_identity:
        logging.info("using the Airlock processor's managed identity to get storage management client")
    return DefaultAzureCredential(managed_identity_client_id=os.environ["MANAGED_IDENTITY_CLIENT_ID"],
                                  exclude_shared_token_cache_credential=True) if managed_identity else DefaultAzureCredential()


def get_blob_info_from_topic_and_subject(topic: str, subject: str):
    # Example of a topic: "/subscriptions/<subscription_id>/resourceGroups/<reosurce_group_name>/providers/Microsoft.Storage/storageAccounts/<storage_account_name>"
    storage_account_name = re.search(r'providers/Microsoft.Storage/storageAccounts/(.*?)$', topic).group(1)
    # Example of a subject: "/blobServices/default/containers/<container_guid>/blobs/<blob_name>"
    container_name, blob_name = re.search(r'/blobServices/default/containers/(.*?)/blobs/(.*?)$', subject).groups()

    return storage_account_name, container_name, blob_name

def get_blob_info_from_blob_url(blob_url: str) -> (str, str, str):
    # If it's the only blob in the container, we need to delete the container too
    # Check how many blobs are in the container
    return re.search(r'https://(.*?).blob.core.windows.net/(.*?)/(.*?)$', blob_url).groups()

