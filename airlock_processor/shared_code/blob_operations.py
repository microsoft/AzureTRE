import os
import datetime
import logging

from azure.core.exceptions import ResourceExistsError
from azure.identity import DefaultAzureCredential
from azure.mgmt.storage import StorageManagementClient
from azure.storage.blob import ContainerSasPermissions, generate_container_sas, BlobServiceClient

from exceptions.TooManyFilesInRequestException import TooManyFilesInRequestException
from exceptions.NoFilesInRequestException import NoFilesInRequestException


class StorageConnectionMetadata:
    account_name: str
    account_key: str
    connection_string: str

    def __init__(self, account_name: str, account_key: str, connection_string: str):
        self.account_name = account_name
        self.account_key = account_key
        self.connection_string = connection_string


def create_container(resource_group: str, storage_account: str, request_id: str,
                     storage_client: StorageManagementClient):
    try:
        container_name = request_id
        blob_service_client = get_blob_client_by_rg_and_account(resource_group, storage_account, storage_client)
        blob_service_client.create_container(container_name)
        logging.info(f'Container created for request id: {request_id}.')
    except ResourceExistsError:
        logging.info(f'Did not create a new container. Container already exists for request id: {request_id}.')


def get_blob_client_by_rg_and_account(resource_group: str, storage_account: str,
                                      storage_client: StorageManagementClient):
    sa_connection = get_storage_connection_string(storage_account, resource_group, storage_client)
    return BlobServiceClient.from_connection_string(sa_connection.connection_string)


def get_storage_connection_string(sa_name: str, resource_group: str, storage_client: StorageManagementClient):
    storage_keys = storage_client.storage_accounts.list_keys(resource_group, sa_name)
    storage_keys = {v.key_name: v.value for v in storage_keys.keys}
    storage_account_key = storage_keys['key1']

    conn_string_base = "DefaultEndpointsProtocol=https;EndpointSuffix=core.windows.net;AccountName={};AccountKey={}"
    sa_connection_string = conn_string_base.format(sa_name, storage_account_key)

    return StorageConnectionMetadata(sa_name, storage_account_key, sa_connection_string)


def get_storage_management_client():
    try:
        subscription_id = os.environ["AZURE_SUBSCRIPTION_ID"]
    except KeyError as e:
        logging.error(f'Missing environment variable: {e}')
        raise

    managed_identity = os.environ.get("MANAGED_IDENTITY_CLIENT_ID")
    if managed_identity:
        logging.info("using the Airlock processor's managed identity to get storage management client")
    credential = DefaultAzureCredential(managed_identity_client_id=os.environ["MANAGED_IDENTITY_CLIENT_ID"],
                                        exclude_shared_token_cache_credential=True) if managed_identity else DefaultAzureCredential()

    return StorageManagementClient(credential, subscription_id)


def copy_data(source_account_name: str, source_account_key: str, sa_source_connection_string: str,
              sa_dest_connection_string: str, request_id: str):
    container_name = request_id

    # token geneation with expiry of 1 hour. since its not shared, we can leave it to expire (no need to track/delete)
    # Remove sas token if not needed: https://github.com/microsoft/AzureTRE/issues/2034
    sas_token = generate_container_sas(account_name=source_account_name,
                                       container_name=container_name,
                                       account_key=source_account_key,
                                       permission=ContainerSasPermissions(read=True),
                                       expiry=datetime.datetime.utcnow() + datetime.timedelta(hours=1))

    # Copy files
    source_blob_service_client = BlobServiceClient.from_connection_string(sa_source_connection_string)
    dest_blob_service_client = BlobServiceClient.from_connection_string(sa_dest_connection_string)

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

    source_blob = source_container_client.get_blob_client(blob_name)

    source_url = f'{source_blob.url}?{sas_token}'
    # source_url = source_blob.url

    copied_blob = dest_blob_service_client.get_blob_client(container_name, source_blob.blob_name)
    copy = copied_blob.start_copy_from_url(source_url)

    try:
        logging.info("Copy operation returned 'copy_id': '%s', 'copy_status': '%s'", copy["copy_id"],
                     copy["copy_status"])
    except KeyError as e:
        logging.error(f"Failed getting operation id and status {e}")
