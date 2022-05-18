# azure-virtual-desktop-bicep

AzureAD-Joined session hosts requires the following:
- Non-overlapping private IP space
- Permissions to grant users the "Virtual Machine User Login" role at the resource group level for to login

## Resources

### Learning Bicep

- [Define resources with Bicep and ARM templates](https://docs.microsoft.com/azure/templates)
- [Bicep modules](https://docs.microsoft.com/azure/azure-resource-manager/templates/bicep-modules)
- [Iterative loops in Bicep](https://docs.microsoft.com/azure/azure-resource-manager/bicep/loop-resources#resource-iteration-with-condition)

### Specific Azure Resource Definitions in Bicep

- [Bicep reference: Microsoft.DesktopVirtualization/hostPools](https://docs.microsoft.com/azure/templates/microsoft.desktopvirtualization/hostpools?tabs=bicep)
- [Bicep reference: Microsoft.DesktopVirtualization/applicationGroups](https://docs.microsoft.com/azure/templates/microsoft.desktopvirtualization/applicationgroups?tabs=bicep)
- [Bicep reference: Microsoft.DesktopVirtualization/workspaces](https://docs.microsoft.com/azure/templates/microsoft.desktopvirtualization/workspaces?tabs=bicep)
- [ARM reference: Microsoft.DesktopVirtualization@2021-07-12](https://github.com/Azure/bicep-types-az/blob/main/generated/desktopvirtualization/microsoft.desktopvirtualization/2021-07-12/types.md)
- [ARM template for VM creation](https://wvdportalstorageblob.blob.core.windows.net/galleryartifacts/armtemplates/Hostpool_12-9-2021/nestedTemplates/managedDisks-galleryvm.json)

## Some notes

The `Microsoft.DesktopVirtualization` namespace isn't well documented yet, so I recommend you reference the [REST API docs](https://docs.microsoft.com/rest/api/desktopvirtualization/) to determine which API versions you should be using.

To research common VM extension error messages, see [Understand common error messages when you manage virtual machines in Azure](https://docs.microsoft.com/troubleshoot/azure/virtual-machines/error-messages).
