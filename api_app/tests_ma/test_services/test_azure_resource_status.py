from mock import patch
from services import azure_resource_status
from azure.mgmt.compute.models import VirtualMachineInstanceView, InstanceViewStatus


@patch("services.azure_resource_status.get_azure_vm_instance_view")
def test_get_azure_resource_status__correct_status_returned_for_vm(get_vm_instance_view_mock):
    status1 = InstanceViewStatus(code="ProvisioningState/succeeded", level="Info", display_status="Provisioning succeeded")
    status2 = InstanceViewStatus(code="PowerState/Running", level="Info", display_status="Running")

    virtual_machine_instance_view_mock: VirtualMachineInstanceView = VirtualMachineInstanceView(statuses=[status1, status2])

    get_vm_instance_view_mock.return_value = virtual_machine_instance_view_mock
    vm_status = azure_resource_status.get_azure_resource_status('/subscriptions/subscription_id/resourceGroups/resource_group_name/providers/Microsoft.Compute/virtualMachines/vm_name')
    assert vm_status == {'powerState': 'Running'}


def test_get_azure_resource_status__empty_status_returned_unknown():

    vm_status = azure_resource_status.get_azure_resource_status('/subscriptions/subscription_id/resourceGroups/resource_group_name/providers/Microsoft.Unknown/resourceType/name')
    assert vm_status == {}
