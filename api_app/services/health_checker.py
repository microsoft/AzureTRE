from typing import Tuple
from azure.core import exceptions
from azure.cosmos.aio import CosmosClient
from azure.servicebus.aio import ServiceBusClient
from azure.mgmt.cosmosdb.aio import CosmosDBManagementClient
from azure.mgmt.compute.aio import ComputeManagementClient
from azure.cosmos.exceptions import CosmosHttpResponseError
from azure.servicebus.exceptions import ServiceBusConnectionError, ServiceBusAuthenticationError

from core import config
from models.schemas.status import StatusEnum
from resources import strings


async def get_store_key(credential) -> str:
    if config.STATE_STORE_KEY:
        primary_master_key = config.STATE_STORE_KEY
    else:
        async with CosmosDBManagementClient(credential, subscription_id=config.SUBSCRIPTION_ID) as cosmosdb_mng_client:
            database_keys = await cosmosdb_mng_client.database_accounts.list_keys(resource_group_name=config.RESOURCE_GROUP_NAME, account_name=config.COSMOSDB_ACCOUNT_NAME)
            primary_master_key = database_keys.primary_master_key
            return primary_master_key


async def create_state_store_status(credential) -> Tuple[StatusEnum, str]:
    status = StatusEnum.ok
    message = ""
    debug = True if config.DEBUG == "true" else False
    try:
        primary_master_key = await get_store_key(credential)
        cosmos_client = CosmosClient(config.STATE_STORE_ENDPOINT, primary_master_key, connection_verify=debug)
        async with cosmos_client:
            list_databases_response = cosmos_client.list_databases()
            [database async for database in list_databases_response]
    except exceptions.ServiceRequestError:
        status = StatusEnum.not_ok
        message = strings.STATE_STORE_ENDPOINT_NOT_RESPONDING
    except CosmosHttpResponseError:
        status = StatusEnum.not_ok
        message = strings.STATE_STORE_ENDPOINT_NOT_ACCESSIBLE
    except:  # noqa: E722 flake8 - no bare excepts
        status = StatusEnum.not_ok
        message = strings.UNSPECIFIED_ERROR
    return status, message


async def create_service_bus_status(credential) -> Tuple[StatusEnum, str]:
    status = StatusEnum.ok
    message = ""
    try:
        service_bus_client = ServiceBusClient(config.SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE, credential, retry_total=0)
        async with service_bus_client:
            receiver = service_bus_client.get_queue_receiver(queue_name=config.SERVICE_BUS_DEPLOYMENT_STATUS_UPDATE_QUEUE)
            async with receiver:
                pass
    except ServiceBusConnectionError:
        status = StatusEnum.not_ok
        message = strings.SERVICE_BUS_NOT_RESPONDING
    except ServiceBusAuthenticationError:
        status = StatusEnum.not_ok
        message = strings.SERVICE_BUS_AUTHENTICATION_ERROR
    except:  # noqa: E722 flake8 - no bare excepts
        status = StatusEnum.not_ok
        message = strings.UNSPECIFIED_ERROR
    return status, message


async def create_resource_processor_status(credential) -> Tuple[StatusEnum, str]:
    status = StatusEnum.ok
    message = ""
    try:
        vmss_name = f"vmss-rp-porter-{config.TRE_ID}"
        compute_client = ComputeManagementClient(credential=credential, subscription_id=config.SUBSCRIPTION_ID)
        async with compute_client:
            vmss_list = compute_client.virtual_machine_scale_set_vms.list(config.RESOURCE_GROUP_NAME, vmss_name)
            async for vm in vmss_list:
                instance_view = await compute_client.virtual_machine_scale_set_vms.get_instance_view(config.RESOURCE_GROUP_NAME, vmss_name, vm.instance_id)
                health_status = instance_view.vm_health.status.code
                if health_status != strings.RESOURCE_PROCESSOR_HEALTHY_MESSAGE:
                    status = StatusEnum.not_ok
                    message = strings.RESOURCE_PROCESSOR_GENERAL_ERROR_MESSAGE
    except:   # noqa: E722 flake8 - no bare excepts
        status = StatusEnum.not_ok
        message = strings.UNSPECIFIED_ERROR
    return status, message
