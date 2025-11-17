import os
import logging
import json
import re
from datetime import datetime, timedelta, UTC
from typing import Tuple

from azure.core.exceptions import ResourceExistsError
from azure.identity import DefaultAzureCredential
from azure.storage.blob import ContainerSasPermissions, generate_container_sas, BlobServiceClient

from exceptions import NoFilesInRequestException, TooManyFilesInRequestException


def get_account_url(account_name: str) -> str:
    return f"https://{account_name}.blob.{get_storage_endpoint_suffix()}/"


def get_blob_client_from_blob_info(storage_account_name: str, container_name: str, blob_name: str):
    source_blob_service_client = BlobServiceClient(account_url=get_account_url(storage_account_name),
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


def get_request_files(account_name: str, request_id: str) -> list:
    files = []
    blob_service_client = BlobServiceClient(account_url=get_account_url(account_name), credential=get_credential())
    container_client = blob_service_client.get_container_client(container=request_id)

    for blob in container_client.list_blobs():
        files.append({"name": blob.name, "size": blob.size})

    return files


def copy_data(source_account_name: str, destination_account_name: str, request_id: str):
    credential = get_credential()
    container_name = request_id

    source_blob_service_client = BlobServiceClient(account_url=get_account_url(source_account_name),
                                                   credential=credential)
    source_container_client = source_blob_service_client.get_container_client(container_name)

    # Check that we are copying exactly one blob
    found_blobs = 0
    blob_name = ""
    for blob in source_container_client.list_blobs():
        blob_name = blob.name
        if found_blobs > 0:
            msg = "Request with id {} contains more than 1 file. flow aborted.".format(request_id)
            logging.error(msg)
            raise TooManyFilesInRequestException(msg)
        found_blobs += 1

    if found_blobs == 0:
        msg = "Request with id {} did not contain any files. flow aborted.".format(request_id)
        logging.error(msg)
        raise NoFilesInRequestException(msg)

    # token geneation with expiry of 1 hour. since its not shared, we can leave it to expire (no need to track/delete)
    # Remove sas token if not needed: https://github.com/microsoft/AzureTRE/issues/2034
    start = datetime.now(UTC) - timedelta(minutes=15)
    expiry = datetime.now(UTC) + timedelta(hours=1)
    udk = source_blob_service_client.get_user_delegation_key(key_start_time=start, key_expiry_time=expiry)

    sas_token = generate_container_sas(container_name=container_name,
                                       account_name=source_account_name,
                                       user_delegation_key=udk,
                                       permission=ContainerSasPermissions(read=True),
                                       start=start,
                                       expiry=expiry)

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
        logging.info("using the Airlock processor's managed identity to get credentials.")
    return DefaultAzureCredential(managed_identity_client_id=os.environ["MANAGED_IDENTITY_CLIENT_ID"],
                                  exclude_shared_token_cache_credential=True) if managed_identity else DefaultAzureCredential()


def get_blob_info_from_topic_and_subject(topic: str, subject: str):
    # Example of a topic: "/subscriptions/<subscription_id>/resourceGroups/<reosurce_group_name>/providers/Microsoft.Storage/storageAccounts/<storage_account_name>"
    storage_account_name = re.search(r'providers/Microsoft.Storage/storageAccounts/(.*?)$', topic).group(1)
    # Example of a subject: "/blobServices/default/containers/<container_guid>/blobs/<blob_name>"
    container_name, blob_name = re.search(r'/blobServices/default/containers/(.*?)/blobs/(.*?)$', subject).groups()

    return storage_account_name, container_name, blob_name


def get_blob_info_from_blob_url(blob_url: str) -> Tuple[str, str, str]:
    # Example of blob url: https://stalimappws663d.blob.core.windows.net/50866a82-d13a-4fd5-936f-deafdf1022ce/test_blob.txt
    return re.search(rf'https://(.*?).blob.{get_storage_endpoint_suffix()}/(.*?)/(.*?)$', blob_url).groups()


def get_blob_url(account_name: str, container_name: str, blob_name='') -> str:
    return f'{get_account_url(account_name)}{container_name}/{blob_name}'


def get_storage_endpoint_suffix():
    default_value = "core.windows.net"
    try:
        return os.environ["STORAGE_ENDPOINT_SUFFIX"]
    except KeyError as e:
        logging.warning(f"Missing environment variable: {e}. using default value: '{default_value}'")
        return default_value
