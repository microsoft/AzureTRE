targetScope = 'subscription'

param id string
param workspaceId string
param treId string
param tags object = {}
param localAdminName string = 'adminuser'
param vmSize string = 'Standard_D2as_v4'

param vmCount int = 1
param deploymentTime string = utcNow()
@secure()
param passwordSeed string = newGuid()

var shortWorkspaceId = substring(workspaceId, length(workspaceId) - 4, 4)
var shortServiceId = substring(id, length(id) - 4, 4)
var workspaceResourceNameSuffix = '${treId}-ws-${shortWorkspaceId}'
var serviceResourceNameSuffix = '${workspaceResourceNameSuffix}-svc-${shortServiceId}'

var deploymentNamePrefix = '${serviceResourceNameSuffix}-{rtype}-${deploymentTime}'

resource workspaceResourceGroup 'Microsoft.Resources/resourceGroups@2021-04-01' existing = {
  name: 'rg-${workspaceResourceNameSuffix}'
}

resource workspaceKeyVault 'Microsoft.KeyVault/vaults@2021-11-01-preview' existing = {
  name: 'kv-${workspaceResourceNameSuffix}'
  scope: workspaceResourceGroup
}

// Doubling up the unique string with the same seed does not increase password entropy,
// but it guarantees that there will be at least three character classes present in the password
// to meet operating system password complexity requirements
// This could be enhanced by specifying a second, different seed GUID
var localAdminPasswordGenerated = '${uniqueString(passwordSeed)}_${toUpper(uniqueString(passwordSeed))}'

var secrets = [
  {
    secretValue: passwordSeed
    secretName: '${shortServiceId}-${deploymentTime}-localadminpwdseed'
  }
  {
    // Generate a new password for the required local VM admin
    secretValue: localAdminPasswordGenerated
    secretName: '${shortServiceId}-${deploymentTime}-localadminpwd'
  }
]

// Persist the new password in the workspace's Key Vault
module keyVaultSecrets 'modules/keyVaultSecret.bicep' = [for (secret, i) in secrets: {
  scope: workspaceResourceGroup
  name: '${replace(deploymentNamePrefix, '{rtype}', 'Secret')}-${i}'
  params: {
    workspaceKeyVaultName: workspaceKeyVault.name
    secretValue: secrets[i].secretValue
    secretName: secrets[i].secretName
  }
}]

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
    localAdminPassword: localAdminPasswordGenerated
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
