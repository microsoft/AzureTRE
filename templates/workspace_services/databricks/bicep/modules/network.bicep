@description('The Azure region for the specified resources.')
param location string = resourceGroup().location

@description('The base name to be appended to all provisioned resources.')
param baseName string

@description('The name of the virtual network.')
param vnetName string

@description('The name of the databricks host subnet.')
param hostSubnetName string

@description('The name of the databricks container subnet.')
param containerSubnetName string

@description('The name of the network security group to be attached to the databricks subnets.')
param networkSecurityGroupName string

@description('The IP space to use for the databricks host subnet.')
param hostSubnetAddressPrefix string

@description('The IP space to use for the databricks container subnet.')
param containerSubnetAddressPrefix string

@description('The name of the route table.')
param routeTableName string

@description('The private IP address of the Azure Firewall.')
param firewallIpAddress string

@description('The tags to be applied to the provisioned resources.')
param tags object

var subnetDetails = [
  {
    name: hostSubnetName
    subnetPrefix: hostSubnetAddressPrefix
    delegationName: 'db-host-vnet-integration'
  }
  {
    name: containerSubnetName
    subnetPrefix: containerSubnetAddressPrefix
    delegationName: 'db-container-vnet-integration'
  }
]

// TO-BE-UPDATED based on https://docs.microsoft.com/en-us/azure/databricks/administration-guide/cloud-configurations/azure/udr#control-plane-nat-and-webapp-ip-addresses
var mapLocationUrlConfig = {
  westeurope: {
    webApp: [
      '52.232.19.246/32'
      '40.74.30.80/32'
    ]
    sccRelay: [
      '23.97.201.41/32'
      '51.138.96.158/32'
    ]
    controlPlaneNat: [
      '23.100.0.135/32'
      '40.74.30.81/32'
    ]
    extendedInfra: [
      '20.73.215.48/28'
    ]
  }
}

resource dbNetworkSecurityGroup 'Microsoft.Network/networkSecurityGroups@2021-02-01' = {
  name: networkSecurityGroupName
  location: location
  tags: tags
  properties: {
    securityRules: [
      {
        name: '${baseName}-nsgsg-001'
        properties: {
          description: 'Required for worker nodes communication within a cluster.'
          protocol: '*'
          sourcePortRange: '*'
          destinationPortRange: '*'
          sourceAddressPrefix: 'VirtualNetwork'
          destinationAddressPrefix: 'VirtualNetwork'
          access: 'Allow'
          priority: 100
          direction: 'Inbound'
        }
      }
      {
        name: '${baseName}-nsgsg-002'
        properties: {
          description: 'Required for workers communication with Databricks Webapp.'
          protocol: 'Tcp'
          sourcePortRange: '*'
          destinationPortRange: '443'
          sourceAddressPrefix: 'VirtualNetwork'
          destinationAddressPrefix: 'AzureDatabricks'
          access: 'Allow'
          priority: 100
          direction: 'Outbound'
        }
      }
      {
        name: '${baseName}-nsgsg-003'
        properties: {
          description: 'Required for workers communication with Azure SQL services.'
          protocol: 'Tcp'
          sourcePortRange: '*'
          destinationPortRange: '3306'
          sourceAddressPrefix: 'VirtualNetwork'
          destinationAddressPrefix: 'Sql'
          access: 'Allow'
          priority: 101
          direction: 'Outbound'
        }
      }
      {
        name: '${baseName}-nsgsg-004'
        properties: {
          description: 'Required for workers communication with Azure Storage services.'
          protocol: 'Tcp'
          sourcePortRange: '*'
          destinationPortRange: '443'
          sourceAddressPrefix: 'VirtualNetwork'
          destinationAddressPrefix: 'Storage'
          access: 'Allow'
          priority: 102
          direction: 'Outbound'
        }
      }
      {
        name: '${baseName}-nsgsg-005'
        properties: {
          description: 'Required for worker nodes communication within a cluster.'
          protocol: '*'
          sourcePortRange: '*'
          destinationPortRange: '*'
          sourceAddressPrefix: 'VirtualNetwork'
          destinationAddressPrefix: 'VirtualNetwork'
          access: 'Allow'
          priority: 103
          direction: 'Outbound'
        }
      }
      {
        name: '${baseName}-nsgsg-006'
        properties: {
          description: 'Required for worker communication with Azure Eventhub services.'
          protocol: 'Tcp'
          sourcePortRange: '*'
          destinationPortRange: '9093'
          sourceAddressPrefix: 'VirtualNetwork'
          destinationAddressPrefix: 'EventHub'
          access: 'Allow'
          priority: 104
          direction: 'Outbound'
        }
      }
    ]
  }
}

resource workspaceVirtualNetwork 'Microsoft.Network/virtualNetworks@2019-11-01' existing = {
  name: vnetName
}

resource routeTable 'Microsoft.Network/routeTables@2021-08-01' = {
  name: routeTableName
  location: location
  tags: tags
  properties: {
    disableBgpRoutePropagation: false
    routes: [
      {
        name: 'to-firewall'
        properties: {
          addressPrefix: '0.0.0.0/0'
          nextHopIpAddress: firewallIpAddress
          nextHopType: 'VirtualAppliance'
        }
        type: 'string'
      }
      {
        name: 'to-databricks-scc-relay-ip'
        properties: {
          addressPrefix: mapLocationUrlConfig[location].sccRelay[0]
          nextHopType: 'Internet'
        }
        type: 'string'
      }
    ]
  }
}

@batchSize(1)
resource subnets 'Microsoft.Network/virtualNetworks/subnets@2020-11-01' = [for (sn, index) in subnetDetails: {
  name: sn.name
  parent: workspaceVirtualNetwork
  properties: {
    addressPrefix: sn.subnetPrefix
    privateEndpointNetworkPolicies: 'Disabled'
    delegations: [
      {
        properties: {
          serviceName: 'Microsoft.Databricks/workspaces'
        }
        name: sn.delegationName
      }
    ]
    networkSecurityGroup: {
      id: dbNetworkSecurityGroup.id
    }
    routeTable: {
      id: routeTable.id
    }
  }
}]

output hostSubnetName string = subnets[0].name
output containerSubnetName string = subnets[1].name
