from azure.core import exceptions
from azure.cosmos import CosmosClient
from azure.identity import DefaultAzureCredential
from azure.mgmt.cosmosdb import CosmosDBManagementClient

from core import config
from models.schemas.status import StatusEnum
from resources import strings


def create_state_store_status() -> (StatusEnum, str):
    status = StatusEnum.ok
    message = ""
    try:
        credential = DefaultAzureCredential(managed_identity_client_id=config.MANAGED_IDENTITY_CLIENT_ID)
        cosmosdb_client = CosmosDBManagementClient(credential, subscription_id=config.SUBSCRIPTION_ID)
        database_keys = cosmosdb_client.database_accounts.list_keys(resource_group_name=config.RESOURCE_GROUP_NAME, account_name=config.COSMOSDB_ACCOUNT_NAME)
        primary_master_key = database_keys.primary_master_key
        client = CosmosClient(config.STATE_STORE_ENDPOINT, primary_master_key)    # noqa: F841 - flake 8 client is not used
    except exceptions.ServiceRequestError:
        status = StatusEnum.not_ok
        message = strings.STATE_STORE_ENDPOINT_NOT_RESPONDING
    except:     # noqa: E722 flake8 - no bare excepts
        status = StatusEnum.not_ok
        message = strings.UNSPECIFIED_ERROR
    return status, message
