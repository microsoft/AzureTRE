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
param deploymentTime string = utcNow()

var shortWorkspaceId = substring(workspaceId, length(workspaceId) - 4, 4)
var shortServiceId = substring(id, length(id) - 4, 4)
var workspaceResourceNameSuffix = '${treId}-ws-${shortWorkspaceId}'
var serviceResourceNameSuffix = '${workspaceResourceNameSuffix}-svc-${shortServiceId}'

var deploymentNamePrefix = '${serviceResourceNameSuffix}-{rtype}-${deploymentTime}'

resource workspaceResourceGroup 'Microsoft.Resources/resourceGroups@2021-04-01' existing = {
  name: 'rg-${workspaceResourceNameSuffix}'
}

resource workspaceVirtualNetwork 'Microsoft.Network/virtualNetworks@2019-11-01' existing = {
  scope: workspaceResourceGroup
  name: 'vnet-${workspaceResourceNameSuffix}'
}

module hostPool 'modules/hostPools.bicep' = {
  scope: workspaceResourceGroup
  name: replace(deploymentNamePrefix, '{rtype}', 'AVD-HostPool')
  params: {
    name: serviceResourceNameSuffix
    tags: tags
    location: workspaceResourceGroup.location
    hostPoolType: 'Pooled'
  }
}

module applicationGroup 'modules/applicationGroup.bicep' = {
  scope: workspaceResourceGroup
  name: replace(deploymentNamePrefix, '{rtype}', 'AVD-ApplicationGroup')
  params: {
    name: serviceResourceNameSuffix
    tags: tags
    location: workspaceResourceGroup.location
    hostPoolId: hostPool.outputs.id
  }
}

module workspace 'modules/workspace.bicep' = {
  scope: workspaceResourceGroup
  name: replace(deploymentNamePrefix, '{rtype}', 'AVD-Workspace')
  params: {
    name: serviceResourceNameSuffix
    tags: tags
    location: workspaceResourceGroup.location
    applicationGroupId: applicationGroup.outputs.id
  }
}

module sessionHost 'modules/sessionHost.bicep' = {
  scope: workspaceResourceGroup
  name: replace(deploymentNamePrefix, '{rtype}', 'AVD-SessionHosts')
  params: {
    name: serviceResourceNameSuffix
    tags: tags
    location: workspaceResourceGroup.location
    localAdminName: localAdminName
    localAdminPassword: localAdminPassword
    subnetName: 'ServicesSubnet'
    vmSize: vmSize
    vmCount: vmCount
    vnetId: workspaceVirtualNetwork.id
    hostPoolName: hostPool.outputs.name
    hostPoolRegToken: hostPool.outputs.token
    deploymentNameStructure: deploymentNamePrefix
  }
}

output connection_uri string = 'https://aka.ms/wvdarmweb'
