import logging

import azure.functions as func
import os
import json

from azure.mgmt.storage import StorageManagementClient
from azure.storage.blob import BlobServiceClient

from shared_code import blob_operations, constants
from pydantic import BaseModel, parse_obj_as

from shared_code.blob_operations import get_storage_management_client


class RequestProperties(BaseModel):
    request_id: str
    status: str
    type: str
    workspace_id: str


class ContainersCopyMetadata:
    source_account_name: str
    source_account_key: str
    sa_source_connection_string: str
    sa_dest_connection_string: str

    def __init__(self, source_account_name: str, source_account_key: str, sa_source_connection_string: str, sa_dest_connection_string: str):
        self.source_account_name = source_account_name
        self.source_account_key = source_account_key
        self.sa_source_connection_string = sa_source_connection_string
        self.sa_dest_connection_string = sa_dest_connection_string


def main(msg: func.ServiceBusMessage):

    body = msg.get_body().decode('utf-8')
    logging.info('Python ServiceBus queue trigger processed message: %s', body)
    storage_client = get_storage_management_client()

    try:
        request_properties = extract_properties(body)

        new_status = request_properties.status
        req_id = request_properties.request_id
        ws_id = request_properties.workspace_id
        request_type = request_properties.type
    except Exception as e:
        logging.error(f'Failed processing request - invalid message: {body}, exc: {e}')
        raise

    logging.info('Processing request with id %s. new status is "%s", type is "%s"', req_id, new_status, type)

    if (is_require_data_copy(new_status)):
        logging.info('Request with id %s. requires data copy between storage accounts', req_id)
        containers_metadata = get_source_dest_env_vars(new_status, request_type, ws_id, storage_client)
        blob_service_client = BlobServiceClient.from_connection_string(containers_metadata.sa_dest_connection_string)
        blob_operations.create_container(blob_service_client, req_id)
        blob_operations.copy_data(containers_metadata.source_account_name, containers_metadata.source_account_key, containers_metadata.sa_source_connection_string, containers_metadata.sa_dest_connection_string, req_id)
        return

    # Todo: handle other cases...


def extract_properties(body: str) -> RequestProperties:
    try:
        json_body = json.loads(body)
        result = parse_obj_as(RequestProperties, json_body["data"])
        if not result:
            raise Exception("Failed parsing request properties")
    except json.decoder.JSONDecodeError:
        logging.error(f'Error decoding object: {body}')
        raise
    except Exception as e:
        logging.error(f'Error extracting properties: {e}')
        raise

    return result


def is_require_data_copy(new_status: str):
    if new_status.lower() in [constants.STAGE_SUBMITTED, constants.STAGE_APPROVED, constants.STAGE_REJECTED, constants.STAGE_BLOCKED]:
        return True
    return False


def get_source_dest_env_vars(new_status: str, request_type: str, short_workspace_id: str, storage_client: StorageManagementClient) -> ContainersCopyMetadata:

    # sanity
    if is_require_data_copy(new_status) is False:
        raise Exception("Given new status is not supported")

    try:
        tre_id = os.environ["TRE_ID"]
    except KeyError as e:
        logging.error(f'Missing environment variable: {e}')
        raise

    request_type = request_type.lower()
    if request_type != constants.IMPORT_TYPE and request_type != constants.EXPORT_TYPE:
        msg = "Airlock request type must be either '{}' or '{}".format(str(constants.IMPORT_TYPE), str(constants.EXPORT_TYPE))
        logging.error(msg)
        raise Exception(msg)

    if request_type == constants.IMPORT_TYPE:
        if new_status == 'submitted':
            source_account_name = constants.STORAGE_ACCOUNT_NAME_IMPORT_EXTERNAL.format(tre_id)
            dest_account_name = constants.STORAGE_ACCOUNT_NAME_IMPORT_INPROGRESS.format(tre_id)
            source_account_rg = constants.CORE_RESOURCE_GROUP_NAME.format(tre_id)
            dest_account_rg = source_account_rg
        elif new_status == 'approved':
            source_account_name = constants.STORAGE_ACCOUNT_NAME_IMPORT_INPROGRESS.format(tre_id)
            dest_account_name = constants.STORAGE_ACCOUNT_NAME_IMPORT_APPROVED.format(short_workspace_id)
            source_account_rg = constants.CORE_RESOURCE_GROUP_NAME.format(tre_id)
            dest_account_rg = constants.WORKSPACE_RESOURCE_GROUP_NAME.format(tre_id, short_workspace_id)
        elif new_status == 'rejected':
            source_account_name = constants.STORAGE_ACCOUNT_NAME_IMPORT_INPROGRESS.format(tre_id)
            dest_account_name = constants.STORAGE_ACCOUNT_NAME_IMPORT_REJECTED.format(tre_id)
            source_account_rg = constants.CORE_RESOURCE_GROUP_NAME.format(tre_id)
            dest_account_rg = source_account_rg
    else:
        if new_status == 'submitted':
            source_account_name = constants.STORAGE_ACCOUNT_NAME_EXPORT_INTERNAL.format(short_workspace_id)
            dest_account_name = constants.STORAGE_ACCOUNT_NAME_EXPORT_INPROGRESS.format(short_workspace_id)
            source_account_rg = constants.WORKSPACE_RESOURCE_GROUP_NAME.format(tre_id, short_workspace_id)
            dest_account_rg = source_account_rg
        elif new_status == 'approved':
            source_account_name = constants.STORAGE_ACCOUNT_NAME_EXPORT_INPROGRESS.format(short_workspace_id)
            dest_account_name = constants.STORAGE_ACCOUNT_NAME_EXPORT_APPROVED.format(tre_id)
            source_account_rg = constants.WORKSPACE_RESOURCE_GROUP_NAME.format(tre_id, short_workspace_id)
            dest_account_rg = constants.CORE_RESOURCE_GROUP_NAME.format(tre_id)
        elif new_status == 'rejected':
            source_account_name = constants.STORAGE_ACCOUNT_NAME_EXPORT_INPROGRESS.format(short_workspace_id)
            dest_account_name = constants.STORAGE_ACCOUNT_NAME_EXPORT_REJECTED.format(short_workspace_id)
            source_account_rg = constants.WORKSPACE_RESOURCE_GROUP_NAME.format(tre_id, short_workspace_id)
            dest_account_rg = source_account_rg

    logging.info("source [account: '%s', rg: '%s']. dest [account: '%s', rg: '%s']", source_account_name, source_account_rg, dest_account_name, dest_account_rg)

    sa_source = blob_operations.get_storage_connection_string(source_account_name, source_account_rg, storage_client)
    sa_dest = blob_operations.get_storage_connection_string(dest_account_name, dest_account_rg, storage_client)

    return ContainersCopyMetadata(sa_source.account_name, sa_source.account_key, sa_source.connection_string, sa_dest.connection_string)
