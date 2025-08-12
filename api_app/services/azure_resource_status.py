from core import config, credentials
import logging

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
                logging.info("statuses object available for VM")
                power_states = [x for x in vm_instance_view.statuses if x.code is not None and x.code.startswith('PowerState')]
                if len(power_states) > 0:
                    logging.info("power_states object available for VM")
                    power_state = power_states[0].display_status
                    logging.info(power_state)
            return {"powerState": power_state}
    except ResourceNotFoundError:
        logging.warning(f"Unable to query resource status for {resource_id}, as the resource was not found.")

    return {}


def get_azure_vm_instance_view(vm_name, resource_group_name) -> models.VirtualMachineInstanceView:
    compute_client = ComputeManagementClient(credentials.get_credential(), config.SUBSCRIPTION_ID)
    return compute_client.virtual_machines.instance_view(resource_group_name, vm_name)
