targetScope = 'subscription'

param id string
param workspaceId string
param treId string
param hostSubnetAddressPrefix string
param containerSubnetAddressPrefix string
param tags object = {}

var shortWorkspaceId = substring(workspaceId, length(workspaceId) - 4, 4)
var shortServiceId = substring(id, length(id) - 4, 4)
var workspaceResourceNameSuffix = '${treId}-ws-${shortWorkspaceId}'
var databricksWorkspaceName = 'dbw-${workspaceResourceNameSuffix}'
var hostSubnetName = 'snet-${workspaceResourceNameSuffix}-host'
var containerSubnetName = 'snet-${workspaceResourceNameSuffix}-container'
var networkSecurityGroupName = 'nsg-${workspaceResourceNameSuffix}'

resource workspaceResourceGroup 'Microsoft.Resources/resourceGroups@2021-04-01' existing = {
  name: 'rg-${workspaceResourceNameSuffix}'
}

resource workspaceStorageAccount 'Microsoft.Resources/resourceGroups@2021-04-01' existing = {
  name: 'stgws${shortWorkspaceId}'
}

resource workspaceKeyVault 'Microsoft.Network/virtualNetworks@2019-11-01' existing = {
  scope: workspaceResourceGroup
  name: 'kv-${workspaceResourceNameSuffix}'
}
module network 'modules/network.bicep' = {
  name: 'networkDeploy'
  scope: workspaceResourceGroup
  params: {
    location: workspaceResourceGroup.location
    baseName: workspaceResourceNameSuffix
    vnetName: 'vnet-${workspaceResourceNameSuffix}'
    hostSubnetName: hostSubnetName
    containerSubnetName: containerSubnetName
    networkSecurityGroupName: networkSecurityGroupName
    hostSubnetAddressPrefix: hostSubnetAddressPrefix
    containerSubnetAddressPrefix: containerSubnetAddressPrefix
    tags: tags
  }
}

module db 'modules/databricks.bicep' = {
  name: 'databricksDeploy'
  scope: workspaceResourceGroup
  params: {
    location: workspaceResourceGroup.location
    baseName: workspaceResourceNameSuffix
    databricksWorkspaceName: databricksWorkspaceName
    vnetName: 'vnet-${workspaceResourceNameSuffix}'
    hostSubnetName: network.outputs.hostSubnetName
    containerSubnetName: network.outputs.containerSubnetName
    tags: tags
  }
}

output databricksWorkspaceName string = db.outputs.databricksWorkspaceName
