from azure.core import exceptions
from azure.cosmos import CosmosClient
from azure.identity.aio import DefaultAzureCredential
from azure.servicebus import ServiceBusClient
from azure.servicebus.exceptions import ServiceBusConnectionError

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

        cosmos_client = CosmosClient(config.STATE_STORE_ENDPOINT, primary_master_key , connection_verify=debug)
        list(cosmos_client.list_databases())
    except exceptions.ServiceRequestError:
        status = StatusEnum.not_ok
        message = strings.STATE_STORE_ENDPOINT_NOT_RESPONDING
    except:     # noqa: E722 flake8 - no bare excepts
        status = StatusEnum.not_ok
        message = strings.UNSPECIFIED_ERROR
    return status, message


def create_service_bus_status() -> (StatusEnum, str):
    status = StatusEnum.ok
    message = ""
    try:
        credential = DefaultAzureCredential(managed_identity_client_id=config.MANAGED_IDENTITY_CLIENT_ID)

        service_bus_client = ServiceBusClient(config.SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE, credential)
        with service_bus_client.get_queue_receiver(queue_name=config.SERVICE_BUS_DEPLOYMENT_STATUS_UPDATE_QUEUE):
            pass
    except ServiceBusConnectionError:
        status = StatusEnum.not_ok
        message = strings.SERVICE_BUS_NOT_RESPONDING
    except:     # noqa: E722 flake8 - no bare excepts
        status = StatusEnum.not_ok
        message = strings.SERVICE_BUS_GENERAL_ERROR_MESSAGE
    return status, message

