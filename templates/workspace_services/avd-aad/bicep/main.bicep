targetScope = 'subscription'

param id string
param workspaceId string
param treId string
param tags object = {}
param localAdminName string = 'adminuser'
@secure()
param localAdminPassword string
param vmSize string = 'Standard_D2as_v4'
param vmCount int = 1
param vmLicenseType string = 'Windows_Client'

var shortWorkspaceId = substring(workspaceId, length(workspaceId) - 4, 4)
var shortServiceId = substring(id, length(id) - 4, 4)
var workspaceResourceNameSuffix = '${treId}-ws-${shortWorkspaceId}'
var serviceResourceNameSuffix = '${workspaceResourceNameSuffix}-svc-${shortServiceId}'

resource workspaceResourceGroup 'Microsoft.Resources/resourceGroups@2021-04-01' existing = {
  name: 'rg-${workspaceResourceNameSuffix}'
}

resource workspaceVirtualNetwork 'Microsoft.Network/virtualNetworks@2019-11-01' existing = {
  scope: workspaceResourceGroup
  name: 'vnet-${workspaceResourceNameSuffix}'
}

module hostPool 'modules/hostPools.bicep' = {
  scope: workspaceResourceGroup
  name: 'hostPoolDeploy'
  params: {
    name: serviceResourceNameSuffix
    tags: tags
    location: workspaceResourceGroup.location
    hostPoolType: 'Pooled'
  }
}

module applicationGroup 'modules/applicationGroup.bicep' = {
  scope: workspaceResourceGroup
  name: 'applicationGroupDeploy'
  params: {
    name: serviceResourceNameSuffix
    tags: tags
    location: workspaceResourceGroup.location
    hostPoolId: hostPool.outputs.id
  }
}

module workspace 'modules/workspace.bicep' = {
  scope: workspaceResourceGroup
  name: 'workspaceDeploy'
  params: {
    name: serviceResourceNameSuffix
    tags: tags
    location: workspaceResourceGroup.location
    applicationGroupId: applicationGroup.outputs.id
  }
}

module sessionHost 'modules/sessionHost.bicep' = {
  scope: workspaceResourceGroup
  name: 'sessionHostDeploy'
  params: {
    name: serviceResourceNameSuffix
    tags: tags
    location: workspaceResourceGroup.location
    localAdminName: localAdminName
    localAdminPassword: localAdminPassword
    subnetName: 'ServicesSubnet'
    vmSize: vmSize
    count: vmCount
    licenseType: vmLicenseType
    vnetId: workspaceVirtualNetwork.id
  }

  dependsOn: [
    hostPool
  ]
}

output connection_uri string = 'https://rdweb.wvd.microsoft.com/arm/webclient/index.html'
