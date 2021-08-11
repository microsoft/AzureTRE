from azure.core import exceptions
from azure.cosmos import CosmosClient
from azure.identity import DefaultAzureCredential
from azure.mgmt.cosmosdb import CosmosDBManagementClient

from api.dependencies.database import get_store_key
from core import config
from models.schemas.status import StatusEnum
from resources import strings


def create_state_store_status() -> (StatusEnum, str):
    status = StatusEnum.ok
    message = ""
    try:
        primary_master_key = get_store_key()
        client = CosmosClient(config.STATE_STORE_ENDPOINT, primary_master_key)    # noqa: F841 - flake 8 client is not used
    except exceptions.ServiceRequestError:
        status = StatusEnum.not_ok
        message = strings.STATE_STORE_ENDPOINT_NOT_RESPONDING
    except:     # noqa: E722 flake8 - no bare excepts
        status = StatusEnum.not_ok
        message = strings.UNSPECIFIED_ERROR
    return status, message
