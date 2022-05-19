targetScope = 'subscription'

param id string
param workspaceId string
param treId string
param hostSubnetAddressPrefix string
param containerSubnetAddressPrefix string
param tags object = {}

var shortWorkspaceId = substring(workspaceId, length(workspaceId) - 4, 4)
var workspaceResourceNameSuffix = '${treId}-ws-${shortWorkspaceId}'

// Existing resources
var resourceGroupName = 'rg-${workspaceResourceNameSuffix}'
var keyVaultName = 'kv-${workspaceResourceNameSuffix}'
var storageAccountName = 'stgws${shortWorkspaceId}'
var virtualNetworkName = 'vnet-${workspaceResourceNameSuffix}'
var firewallName = 'fw-${treId}'
var coreResourceGroupName = 'rg-${treId}'

var databricksWorkspaceName = 'dbw-${workspaceResourceNameSuffix}'
var hostSubnetName = 'snet-${workspaceResourceNameSuffix}-host'
var containerSubnetName = 'snet-${workspaceResourceNameSuffix}-container'
var networkSecurityGroupName = 'nsg-${workspaceResourceNameSuffix}'
var routeTableName = 'rt-${workspaceResourceNameSuffix}'

resource workspaceResourceGroup 'Microsoft.Resources/resourceGroups@2021-04-01' existing = {
  name: resourceGroupName
}

resource workspaceStorageAccount 'Microsoft.Resources/resourceGroups@2021-04-01' existing = {
  name: storageAccountName
}

resource workspaceKeyVault 'Microsoft.Network/virtualNetworks@2019-11-01' existing = {
  scope: workspaceResourceGroup
  name: keyVaultName
}

resource firewall 'Microsoft.Network/azureFirewalls@2021-08-01' existing = {
  name: firewallName
  scope: resourceGroup(coreResourceGroupName)
}

module network 'modules/network.bicep' = {
  name: 'networkDeploy'
  scope: workspaceResourceGroup
  params: {
    location: workspaceResourceGroup.location
    baseName: workspaceResourceNameSuffix
    vnetName:virtualNetworkName
    hostSubnetName: hostSubnetName
    containerSubnetName: containerSubnetName
    networkSecurityGroupName: networkSecurityGroupName
    hostSubnetAddressPrefix: hostSubnetAddressPrefix
    containerSubnetAddressPrefix: containerSubnetAddressPrefix
    routeTableName: routeTableName
    firewallIpAddress: firewall.properties.ipConfigurations[0].properties.privateIPAddress
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
    vnetName: virtualNetworkName
    hostSubnetName: network.outputs.hostSubnetName
    containerSubnetName: network.outputs.containerSubnetName
    tags: tags
  }
}

output databricksWorkspaceName string = db.outputs.databricksWorkspaceName
