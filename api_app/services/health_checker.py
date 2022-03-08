from contextlib import asynccontextmanager

from azure.core import exceptions
from azure.cosmos import CosmosClient
from azure.identity.aio import DefaultAzureCredential
from azure.servicebus.aio import ServiceBusClient
from azure.servicebus.exceptions import ServiceBusConnectionError
from fastapi import HTTPException, status

from api.dependencies.database import get_store_key
from core import config
from models.schemas.status import StatusEnum
from resources import strings


@asynccontextmanager
async def default_credentials():
    """
    Context manager which yields the default credentials.
    """
    credential = DefaultAzureCredential(managed_identity_client_id=config.MANAGED_IDENTITY_CLIENT_ID)
    yield credential
    await credential.close()


def create_state_store_status() -> (StatusEnum, str):
    request_status = StatusEnum.ok
    message = ""
    debug = True if config.DEBUG == "true" else False
    try:
        primary_master_key = get_store_key()

        cosmos_client = CosmosClient(config.STATE_STORE_ENDPOINT, primary_master_key, connection_verify=debug)
        list(cosmos_client.list_databases())
    except exceptions.ServiceRequestError:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail=strings.STATE_STORE_ENDPOINT_NOT_RESPONDING)
    except:  # noqa: E722 flake8 - no bare excepts
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=strings.UNSPECIFIED_ERROR)
    return request_status, message


async def create_service_bus_status() -> (StatusEnum, str):
    request_status = StatusEnum.ok
    message = ""
    try:
        async with default_credentials() as credential:
            service_bus_client = ServiceBusClient(config.SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE, credential,
                                                  retry_total=0)
            async with service_bus_client:
                receiver = service_bus_client.get_queue_receiver(
                    queue_name=config.SERVICE_BUS_DEPLOYMENT_STATUS_UPDATE_QUEUE)
                async with receiver:
                    pass
    except ServiceBusConnectionError:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=strings.SERVICE_BUS_NOT_RESPONDING)
    except:  # noqa: E722 flake8 - no bare excepts
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=strings.UNSPECIFIED_ERROR)
    return request_status, message
