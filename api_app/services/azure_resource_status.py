from core import config
import logging

from azure.identity import DefaultAzureCredential
from azure.mgmt.compute import ComputeManagementClient, models
from azure.core.exceptions import ResourceNotFoundError


def get_azure_resource_status(resource_id):

    resource_name = resource_id.split('/')[-1]
    resource_group_name = resource_id.split('/')[4]
    resource_type = resource_id.split('/')[-3] + '/' + resource_id.split('/')[-2]

    try:
        if resource_type == 'Microsoft.Compute/virtualMachines':
            vm_instance_view: models.VirtualMachineInstanceView = get_azure_vm_instance_view(resource_name, resource_group_name)
            power_state = [x for x in vm_instance_view.statuses if x.code.startswith('PowerState')][0].display_status
            return {"powerState": power_state}
    except ResourceNotFoundError:
        logging.warning(f"Unable to query resource status for {resource_id}, as the resource was not found.")

    return {}


def get_azure_vm_instance_view(vm_name, resource_group_name) -> models.VirtualMachineInstanceView:

    credential = DefaultAzureCredential(managed_identity_client_id=config.MANAGED_IDENTITY_CLIENT_ID)
    compute_client = ComputeManagementClient(credential, config.SUBSCRIPTION_ID)
    return compute_client.virtual_machines.instance_view(resource_group_name, vm_name)
