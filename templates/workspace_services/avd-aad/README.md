# azure-virtual-desktop-bicep

AzureAD-Joined session hosts requires the following:
- Non-overlapping private IP space
- Permissions to grant users the "Virtual Machine User Login" role at the resource group level for to login

## Resources

- https://github.com/Azure/bicep/blob/main/docs/cicd-with-bicep.md
- https://docs.microsoft.com/en-us/azure/templates
- https://docs.microsoft.com/en-us/azure/azure-resource-manager/templates/bicep-modules
- https://docs.microsoft.com/en-us/azure/azure-resource-manager/bicep/loop-resources#resource-iteration-with-condition
- https://docs.microsoft.com/en-us/azure/templates/
- https://docs.microsoft.com/en-us/azure/templates/microsoft.network/virtualnetworks?tabs=bicep
- https://docs.microsoft.com/en-us/azure/templates/microsoft.network/networksecuritygroups?tabs=bicep
- https://docs.microsoft.com/en-us/azure/templates/microsoft.compute/virtualmachines?tabs=bicep
- https://docs.microsoft.com/en-us/rest/api/desktopvirtualization/host-pools/create-or-update
- https://docs.microsoft.com/en-us/rest/api/desktopvirtualization/application-groups/create-or-update
- https://docs.microsoft.com/en-us/rest/api/desktopvirtualization/workspaces/create-or-update
- https://docs.microsoft.com/en-us/azure/api-management/api-management-using-with-vnet#-common-network-configuration-issues
- https://github.com/Azure/bicep-types-az/blob/main/generated/desktopvirtualization/microsoft.desktopvirtualization/2021-07-12/types.md
- https://catalogartifact.azureedge.net/publicartifacts/Microsoft.Hostpool-ARM-1.10.0/managedDisks-galleryvm.json
- https://docs.microsoft.com/en-us/cli/azure/desktopvirtualization?view=azure-cli-latest

## Some notes

The `Microsoft.DesktopVirtualization` namespace isn't well documented yet in https://docs.microsoft.com/en-us/azure/templates/, so I recommend you reference the REST API docs to determine which API versions you should be using https://docs.microsoft.com/en-us/rest/api/desktopvirtualization/.

Common VM extension error messages: https://docs.microsoft.com/en-us/troubleshoot/azure/virtual-machines/error-messages
