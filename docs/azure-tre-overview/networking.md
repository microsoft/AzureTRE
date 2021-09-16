# Network Architecture

The Trusted Research Environment (TRE) network topology is based on [hub-spoke](https://docs.microsoft.com/en-us/azure/architecture/reference-architectures/hybrid-networking/hub-spoke). The TRE Management VNET ([Azure Virtual Network](https://docs.microsoft.com/en-us/azure/virtual-network/virtual-networks-overview)) is the central hub and each workspace is a spoke.

> Note: TRE Management is referred to as **core** in scripts and code.

![Network architecture](../assets/network-architecture.png)

Azure TRE VNETs are segregated allowing limited traffic between the TRE Management VNET and Workspace VNETs. The security rules are managed by `nsg-ws` network security group. See [workspace network security groups (NSG)](#workspaces) further down.

The Core VNET is further divided into subnets.

| Subnet | Description |
| -------| ----------- |
| `AzureBastionSubnet` | A dedicated subnet for Azure Bastion hosts. |
| `AppGwSubnet` | Subnet for Azure Application Gateway controlling ingress traffic. |
| `AzureFirewallSubnet` | Subnet for Azure Firewall controlling egress traffic. |
| `ResourceProcessorSubnet` | Subnet for VMSS used by the Composition Service to host Docker containers to execute Porter bundles that deploys Workspaces. |
| `WebAppSubnet` | Subnet for TRE API. |
| `SharedSubnet` | Shared Services subnet for all things shared by TRE Core and Workspaces. Such as Source Mirror Shared Service and Package Mirror Shared Service. |

All subnets (Core and Workspace subnets) has a default route which directs egress traffic to the Azure Firewall, to ensure only explicitly allowed destinations on the Internet to be accessed.
There are a couple of exceptions

- `AzureFirewallSubnet` as it hosts the Azure Firewall which routes traffic to the Internet.
- `AzureBastionSubnet` as it hosts [Azure Bastion](https://azure.microsoft.com/en-us/services/azure-bastion) which is the management jump box within the VNET with Internet access.
- `AppGwSubnet` as it hosts the Azure Application Gateway which has to be able to a ping the health endpoints e.g. TRE API.

## Ingress and egress

Ingress traffic from the Internet is only allowed through the Application Gateway, which forwards HTTPS (port 443) call to the TRE API in the `WebAppSubnet`.

Egress traffic is routed through the Azure Firewall with a few exceptions and by default all ingress and egress traffic is denied except explicitly allowed.

The explicitly allowed egress traffic is described here:

- [Resource Processor](composition-service/resource-processor.md#network-requirements)
- [TRE API](composition-service/api.md#network-requirements)
- [Gitea Shared Service](shared-services/gitea.md#network-requirements)
- [Nexus Shared Service](shared-services/nexus-shared-service.md#network-requirements)

## Network security groups

### TRE Management/core

Network security groups (NSG), and their security rules for TRE core resources are defined in `/templates/core/terraform/network/network_security_groups.tf`.

| Network security group | Associated subnet(s) |
| ---------------------- | -------------------- |
| `nsg-bastion-subnet` | `AzureBastionSubnet` |
| `nsg-app-gw` | `AppGwSubnet` |
| `nsg-default-rules` | `ResourceProcessorSubnet`, `SharedSubnet`, `WebAppSubnet` |

### Workspaces

Azure TRE VNETs are segregated allowing limited traffic between the TRE Management VNET and Workspace VNETs. The rules to manage and limit the traffic between the TRE Management VNET and Workspace VNETs are defined by the `nsg-ws` network security group:

- Inbound traffic from TRE Management VNET to workspace allowed for [Azure Bastion](https://docs.microsoft.com/en-us/azure/bastion/bastion-overview) (22, 3389) - All other inbound traffic from Core to workspace denied.
- Outbound traffic to `SharedSubnet` from Workspace allowed.
- Outbound traffic to Internet allowed on HTTPS port 443 (next hop Azure Firewall).
- All other outbound traffic denied.

> In Azure, traffic between subnets are allowed except explicitly denied.

Each of these rules can be managed per workspace.
