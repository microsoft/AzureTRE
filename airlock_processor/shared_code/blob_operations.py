import os
import datetime
import logging

from azure.core.exceptions import ResourceExistsError
from azure.identity import DefaultAzureCredential
from azure.storage.blob import ContainerSasPermissions, generate_container_sas, BlobServiceClient

from exceptions.TooManyFilesInRequestException import TooManyFilesInRequestException
from exceptions.NoFilesInRequestException import NoFilesInRequestException


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

    # Copy files
    dest_blob_service_client = BlobServiceClient(account_url=get_account_url(destination_account_name),
                                                 credential=credential)
    copied_blob = dest_blob_service_client.get_blob_client(container_name, source_blob.blob_name)
    copy = copied_blob.start_copy_from_url(source_url)

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


def get_account_url(account_name: str) -> str:
    return f"https://{account_name}.blob.core.windows.net/"
