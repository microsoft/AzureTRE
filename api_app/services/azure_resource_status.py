from core import config, credentials
from services.logging import logger

from azure.mgmt.compute import ComputeManagementClient, models
from azure.core.exceptions import ResourceNotFoundError


def get_azure_resource_status(resource_id):

    resource_name = resource_id.split('/')[-1]
    resource_group_name = resource_id.split('/')[4]
    resource_type = resource_id.split('/')[-3] + '/' + resource_id.split('/')[-2]

    try:
        if resource_type == 'Microsoft.Compute/virtualMachines':
            vm_instance_view: models.VirtualMachineInstanceView = get_azure_vm_instance_view(resource_name, resource_group_name)
            power_state = None
            if vm_instance_view.statuses is not None:
                power_states = [x for x in vm_instance_view.statuses if x.code is not None and x.code.startswith('PowerState')]
                if len(power_states) > 0:
                    power_state = power_states[0].display_status
            return {"powerState": power_state}
    except ResourceNotFoundError:
        logger.warning(f"Unable to query resource status for {resource_id}, as the resource was not found.")

    return {}


def get_azure_vm_instance_view(vm_name, resource_group_name) -> models.VirtualMachineInstanceView:
    compute_client = ComputeManagementClient(credentials.get_credential(),
                                             subscription_id=config.SUBSCRIPTION_ID,
                                             base_url=config.RESOURCE_MANAGER_ENDPOINT,
                                             credential_scopes=config.CREDENTIAL_SCOPES)
    return compute_client.virtual_machines.instance_view(resource_group_name, vm_name)
