import os
import logging
import json
import re
import time
from datetime import datetime, timedelta, UTC
from typing import Tuple

from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
from azure.identity import DefaultAzureCredential
from azure.storage.blob import ContainerSasPermissions, generate_container_sas, BlobServiceClient

from exceptions import NoFilesInRequestException, TooManyFilesInRequestException

COPY_TIMEOUT_SECONDS = 300
COPY_POLL_INTERVAL_SECONDS = 2
SUBMISSION_SEALED_METADATA_KEY = "submission_sealed"


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


def container_exists(account_name: str, container_name: str) -> bool:
    blob_service_client = BlobServiceClient(account_url=get_account_url(account_name),
                                            credential=get_credential())
    return blob_service_client.get_container_client(container_name).exists()


def delete_container(account_name: str, container_name: str):
    blob_service_client = BlobServiceClient(account_url=get_account_url(account_name),
                                            credential=get_credential())
    try:
        blob_service_client.delete_container(container_name)
        logging.info(f'Deleted container {container_name} from {account_name}.')
    except ResourceNotFoundError:
        logging.info(f'Container {container_name} already absent from {account_name}.')


def get_request_files(account_name: str, request_id: str, container_name: str = None) -> list:
    files = []
    blob_service_client = BlobServiceClient(account_url=get_account_url(account_name), credential=get_credential())
    container_client = blob_service_client.get_container_client(container=container_name or request_id)

    for blob in container_client.list_blobs():
        files.append({"name": blob.name, "size": blob.size})

    return files


def is_submission_sealed(account_name: str, container_name: str) -> bool:
    """Return whether the container has one successfully copied, immutable submission blob."""
    blob_service_client = BlobServiceClient(account_url=get_account_url(account_name), credential=get_credential())
    container_client = blob_service_client.get_container_client(container_name)
    blobs = list(container_client.list_blobs())
    if len(blobs) != 1:
        return False

    properties = container_client.get_blob_client(blobs[0].name).get_blob_properties()
    copy_status = getattr(getattr(properties, "copy", None), "status", None)
    return properties.metadata.get(SUBMISSION_SEALED_METADATA_KEY) == "true" and copy_status == "success"


def delete_failed_submission_copy(account_name: str, container_name: str) -> bool:
    """Delete the single destination blob left by an aborted or failed copy."""
    blob_service_client = BlobServiceClient(account_url=get_account_url(account_name), credential=get_credential())
    container_client = blob_service_client.get_container_client(container_name)
    blobs = list(container_client.list_blobs())
    if len(blobs) != 1:
        return False

    blob_client = container_client.get_blob_client(blobs[0].name)
    properties = blob_client.get_blob_properties()
    copy_status = getattr(getattr(properties, "copy", None), "status", None)
    if copy_status not in ("aborted", "failed"):
        return False

    blob_client.delete_blob()
    logging.info(
        "Deleted incomplete submission blob '%s' after copy status '%s' so delivery can retry",
        blobs[0].name, copy_status)
    return True


def copy_data(source_account_name: str, destination_account_name: str, request_id: str,
              source_container: str = None, destination_container: str = None,
              additional_metadata: dict = None):
    credential = get_credential()
    container_name = source_container or request_id
    dest_container_name = destination_container or request_id

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
    metadata = source_blob.get_blob_properties()["metadata"].copy()
    copied_from = json.loads(metadata["copied_from"]) if "copied_from" in metadata else []
    metadata["copied_from"] = json.dumps(copied_from + [source_blob.url])
    if additional_metadata:
        metadata.update(additional_metadata)

    # Copy files
    dest_blob_service_client = BlobServiceClient(account_url=get_account_url(destination_account_name),
                                                 credential=credential)
    copied_blob = dest_blob_service_client.get_blob_client(dest_container_name, source_blob.blob_name)
    copy = copied_blob.start_copy_from_url(source_url, metadata=metadata)

    try:
        logging.info("Copy operation returned 'copy_id': '%s', 'copy_status': '%s'", copy["copy_id"],
                     copy["copy_status"])
    except KeyError as e:
        logging.error(f"Failed getting operation id and status {e}")

    # An async copy still reads from the source, so the caller must not delete it until this settles.
    copy_status = copy.get("copy_status")
    waited_seconds = 0
    while copy_status == "pending" and waited_seconds < COPY_TIMEOUT_SECONDS:
        time.sleep(COPY_POLL_INTERVAL_SECONDS)
        waited_seconds += COPY_POLL_INTERVAL_SECONDS
        copy_status = copied_blob.get_blob_properties().copy.status

    if copy_status != "success":
        if copy_status == "pending":
            # Abort the copy so a late completion cannot recreate the destination after we fail,
            # which would otherwise leave orphaned data once the source is deleted.
            try:
                copied_blob.abort_copy(copy["copy_id"])
                logging.warning(f"Aborted still-pending copy of '{source_blob.blob_name}' after {waited_seconds}s")
            except Exception as abort_error:
                logging.error(f"Failed aborting pending copy of '{source_blob.blob_name}': {abort_error}")
        raise Exception(f"Copy of '{source_blob.blob_name}' did not complete: status '{copy_status}' after {waited_seconds}s")


def get_credential() -> DefaultAzureCredential:
    managed_identity = os.environ.get("MANAGED_IDENTITY_CLIENT_ID")
    if managed_identity:
        logging.info("using the Airlock processor's managed identity to get credentials.")
    return DefaultAzureCredential(managed_identity_client_id=os.environ["MANAGED_IDENTITY_CLIENT_ID"],
                                  exclude_shared_token_cache_credential=True) if managed_identity else DefaultAzureCredential()


def get_blob_info_from_topic_and_subject(topic: str, subject: str):
    # Example of a topic: "/subscriptions/<subscription_id>/resourceGroups/<reosurce_group_name>/providers/Microsoft.Storage/storageAccounts/<storage_account_name>"
    account_match = re.search(r'providers/Microsoft.Storage/storageAccounts/(.*?)$', topic)
    if account_match is None:
        raise ValueError(f"Could not parse storage account name from Event Grid topic: '{topic}'")
    storage_account_name = account_match.group(1)
    # Example of a subject: "/blobServices/default/containers/<container_guid>/blobs/<blob_name>"
    subject_match = re.search(r'/blobServices/default/containers/(.*?)/blobs/(.*?)$', subject)
    if subject_match is None:
        raise ValueError(f"Could not parse container and blob name from Event Grid subject: '{subject}'")
    container_name, blob_name = subject_match.groups()

    return storage_account_name, container_name, blob_name


def get_blob_info_from_blob_url(blob_url: str) -> Tuple[str, str, str]:
    # Example of blob url: https://stalimappws663d.blob.core.windows.net/50866a82-d13a-4fd5-936f-deafdf1022ce/test_blob.txt
    url_match = re.search(rf'https://(.*?).blob.{get_storage_endpoint_suffix()}/(.*?)/(.*?)$', blob_url)
    if url_match is None:
        raise ValueError(f"Could not parse account, container and blob name from blob URL: '{blob_url}'")
    return url_match.groups()


def get_blob_url(account_name: str, container_name: str, blob_name='') -> str:
    return f'{get_account_url(account_name)}{container_name}/{blob_name}'


def get_storage_endpoint_suffix():
    default_value = "core.windows.net"
    try:
        return os.environ["STORAGE_ENDPOINT_SUFFIX"]
    except KeyError as e:
        logging.warning(f"Missing environment variable: {e}. using default value: '{default_value}'")
        return default_value
