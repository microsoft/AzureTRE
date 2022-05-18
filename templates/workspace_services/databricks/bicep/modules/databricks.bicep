@description('The Azure region for the specified resources.')
param location string = resourceGroup().location

@description('The base name to be appended to all provisioned resources.')
param baseName string

@description('The name of the Azure Databricks workspace.')
param databricksWorkspaceName string

@description('The name of the virtual network used by Azure Databricks.')
param vnetName string

@description('The name of the databricks host subnet.')
param hostSubnetName string

@description('The name of the databricks container subnet.')
param containerSubnetName string

@description('The tags to be applied to the provisioned resources.')
param tags object

resource databricks 'Microsoft.Databricks/workspaces@2018-04-01' = {
  name: databricksWorkspaceName
  location: location
  tags: tags
  sku: {
    name: 'premium'
  }
  properties: {
    managedResourceGroupId: '${subscription().id}/resourceGroups/mrg-db-${baseName}'
    parameters: {
      customVirtualNetworkId: {
        value: resourceId('Microsoft.Network/virtualNetworks', vnetName)
      }
      customPrivateSubnetName: {
        value: containerSubnetName
      }
      customPublicSubnetName: {
        value: hostSubnetName
      }
      enableNoPublicIp: {
        value: true
      }
      requireInfrastructureEncryption: {
        value: true
      }

    }
  }

}

output databricksWorkspaceName string = databricks.name
output databricksStorageAccountName string = databricks.properties.parameters.storageAccountName.value
