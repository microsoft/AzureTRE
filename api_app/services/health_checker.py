from azure.core import exceptions
from azure.cosmos import CosmosClient

from api.dependencies.database import get_store_key
from core import config
from models.schemas.status import StatusEnum
from resources import strings


def create_state_store_status() -> (StatusEnum, str):
    status = StatusEnum.ok
    message = ""
    debug = True if config.DEBUG == "true" else False
    try:
        primary_master_key = get_store_key()

        CosmosClient(config.STATE_STORE_ENDPOINT, primary_master_key, connection_verify=debug)
    except exceptions.ServiceRequestError:
        status = StatusEnum.not_ok
        message = strings.STATE_STORE_ENDPOINT_NOT_RESPONDING
    except:     # noqa: E722 flake8 - no bare excepts
        status = StatusEnum.not_ok
        message = strings.UNSPECIFIED_ERROR
    return status, message
