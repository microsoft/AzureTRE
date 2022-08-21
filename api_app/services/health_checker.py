from azure.core import exceptions
from azure.cosmos import CosmosClient
from azure.servicebus.aio import ServiceBusClient
from azure.servicebus.exceptions import ServiceBusConnectionError
from azure.mgmt.compute import ComputeManagementClient

from api.dependencies.database import get_store_key
from core import config, credentials
from models.schemas.status import StatusEnum
from resources import strings


def create_state_store_status() -> (StatusEnum, str):
    status = StatusEnum.ok
    message = ""
    debug = True if config.DEBUG == "true" else False
    try:
        primary_master_key = get_store_key()

        cosmos_client = CosmosClient(config.STATE_STORE_ENDPOINT, primary_master_key, connection_verify=debug)
        list(cosmos_client.list_databases())
    except exceptions.ServiceRequestError:
        status = StatusEnum.not_ok
        message = strings.STATE_STORE_ENDPOINT_NOT_RESPONDING
    except:  # noqa: E722 flake8 - no bare excepts
        status = StatusEnum.not_ok
        message = strings.UNSPECIFIED_ERROR
    return status, message


async def create_service_bus_status() -> (StatusEnum, str):
    status = StatusEnum.ok
    message = ""
    try:
        async with credentials.get_credential_async() as credential:
            service_bus_client = ServiceBusClient(config.SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE, credential,
                                                  retry_total=0)
            async with service_bus_client:
                receiver = service_bus_client.get_queue_receiver(
                    queue_name=config.SERVICE_BUS_DEPLOYMENT_STATUS_UPDATE_QUEUE)
                async with receiver:
                    pass
    except ServiceBusConnectionError:
        status = StatusEnum.not_ok
        message = strings.SERVICE_BUS_NOT_RESPONDING
    except:  # noqa: E722 flake8 - no bare excepts
        status = StatusEnum.not_ok
        message = strings.UNSPECIFIED_ERROR
    return status, message


def create_resource_processor_status() -> (StatusEnum, str):
    status = StatusEnum.ok
    message = ""
    try:
        vmss_name = f"vmss-rp-porter-{config.TRE_ID}"
        compute_client = ComputeManagementClient(credential=credentials.get_credential(), subscription_id=config.SUBSCRIPTION_ID)
        vmss_list = compute_client.virtual_machine_scale_set_vms.list(config.RESOURCE_GROUP_NAME, vmss_name)
        for vm in vmss_list:
            instance_view = compute_client.virtual_machine_scale_set_vms.get_instance_view(config.RESOURCE_GROUP_NAME, vmss_name, vm.instance_id)
            health_status = instance_view.vm_health.status.code
            if health_status != strings.RESOURCE_PROCESSOR_HEALTHY_MESSAGE:
                status = StatusEnum.not_ok
                message = strings.RESOURCE_PROCESSOR_GENERAL_ERROR_MESSAGE
    except:  # noqa: E722 flake8 - no bare excepts
        status = StatusEnum.not_ok
        message = strings.UNSPECIFIED_ERROR
    return status, message
