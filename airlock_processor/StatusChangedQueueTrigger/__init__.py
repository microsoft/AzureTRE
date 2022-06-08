import logging
from pickle import NONE

import azure.functions as func
import os
import json
from shared_code import blob_operations
from azure.identity import DefaultAzureCredential
from azure.mgmt.storage import StorageManagementClient


def main(msg: func.ServiceBusMessage):

    body = msg.get_body().decode('utf-8')
    logging.info('Python ServiceBus queue trigger processed message: %s', body)

    try:
        req_id, new_status, request_type, tre_id, workspace_id = extract_properties(body)
    except Exception:
        logging.error('Failed processing request - invalid message: %s', body)
        raise()

    logging.info('Processing request with id %s. new status is "%s", type is "%s"', req_id, new_status, type)

    if (is_require_data_copy(new_status)):
        logging.info('Request with id %s. requires data copy between storage accounts', req_id)
        source_account_name, source_account_key, sa_source_connection_string, sa_dest_connection_string = get_source_dest_env_vars(new_status, request_type, tre_id, workspace_id)
        blob_operations.copy_data(source_account_name, source_account_key, sa_source_connection_string, sa_dest_connection_string, req_id)
        return

    # Todo: handle other cases...


def extract_properties(body: str):
    try:
        json_body = json.loads(body)
        req_id = json_body["request_id"]
        new_status = json_body["new_status"]
        request_type = json_body["type"]
        tre_id = json_body["tre_id"]
        workspace_id = json_body["workspace_id"]
    except KeyError:
        raise
    except json.decoder.JSONDecodeError:
        raise

    return req_id, new_status, request_type, tre_id, workspace_id


def is_require_data_copy(new_status: str):
    if new_status.lower() in ["submitted", "approved", "rejected", "blocked"]:
        return True
    return False


def get_source_dest_env_vars(new_status: str, request_type: str, tre_id: str, workspace_id: str):
    # sanity
    if is_require_data_copy(new_status) is False:
        raise Exception("Given new status is not supported")

    request_type = request_type.lower()
    if request_type != "import" and request_type != "export":
        raise Exception("Request type must be either import or export")

    if new_status == 'submitted' and request_type == 'import':
        source_account_name = "stalexim{}".format(tre_id)
        dest_account_name = "stalipim{}".format(tre_id)
        source_account_rg = "rg-{}".format(tre_id)
        dest_account_rg = source_account_rg
        logging.info("source account [%s rg: %s]. dest account [%s rg: %s]", source_account_name, source_account_rg, dest_account_name, dest_account_rg)
    elif new_status == 'submitted' and request_type == 'export':
        source_account_name = "stalexint{}".format(tre_id)
        dest_account_name = "stalexip{}".format(tre_id)
        source_account_rg = "rg-{}-ws-{}".format(tre_id, workspace_id)
        dest_account_rg = source_account_rg
        logging.info("source account [%s rg: %s]. dest account [%s rg: %s]", source_account_name, source_account_rg, dest_account_name, dest_account_rg)
    elif new_status == 'approved' and request_type == 'import':
        # https://github.com/microsoft/AzureTRE/issues/1841
        pass
    elif new_status == 'approved' and request_type == 'export':
        # https://github.com/microsoft/AzureTRE/issues/1841
        pass
    elif new_status == 'rejected' and request_type == 'import':
        # https://github.com/microsoft/AzureTRE/issues/1842
        pass
    elif new_status == 'rejected' and request_type == 'export':
        # https://github.com/microsoft/AzureTRE/issues/1842
        pass

    subscription_id = os.environ["AZURE_SUBSCRIPTION_ID"]

    if os.environ.get('ENABLE_LOCAL_DEBUG', NONE) is not NONE:
        # Using the logged-in user
        credential = DefaultAzureCredential()
    else:
        logging.info("using the Airlock processor's managed identity to get build storage management client")
        credential = DefaultAzureCredential(managed_identity_client_id=os.environ["MANAGED_IDENTITY_CLIENT_ID"], exclude_shared_token_cache_credential=True)

    storage_client = StorageManagementClient(credential, subscription_id)
    source_storage_keys = storage_client.storage_accounts.list_keys(source_account_rg, source_account_name)
    source_storage_keys = {v.key_name: v.value for v in source_storage_keys.keys}

    dest_storage_keys = storage_client.storage_accounts.list_keys(dest_account_rg, dest_account_name)
    dest_storage_keys = {v.key_name: v.value for v in dest_storage_keys.keys}

    conn_string_base = "DefaultEndpointsProtocol=https;EndpointSuffix=core.windows.net;AccountName={};AccountKey={}"
    source_account_key = source_storage_keys['key1']
    sa_source_connection_string = conn_string_base.format(source_account_name, source_account_key)
    dest_account_key = dest_storage_keys['key1']
    sa_dest_connection_string = conn_string_base.format(dest_account_name, dest_account_key)

    return source_account_name, source_account_key, sa_source_connection_string, sa_dest_connection_string
