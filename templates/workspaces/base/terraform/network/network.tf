resource "azurerm_virtual_network" "ws" {
  name                = "vnet-${local.workspace_resource_name_suffix}"
  location            = var.location
  resource_group_name = var.ws_resource_group_name
  address_space       = local.address_spaces
  tags                = var.tre_workspace_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_subnet" "services" {
  name                 = "ServicesSubnet"
  virtual_network_name = azurerm_virtual_network.ws.name
  resource_group_name  = var.ws_resource_group_name
  address_prefixes     = [local.services_subnet_address_prefix]
  # notice that private endpoints do not adhere to NSG rules
  private_endpoint_network_policies             = "Disabled"
  private_link_service_network_policies_enabled = true
}

resource "azurerm_subnet" "webapps" {
  name                 = "WebAppsSubnet"
  virtual_network_name = azurerm_virtual_network.ws.name
  resource_group_name  = var.ws_resource_group_name
  address_prefixes     = [local.webapps_subnet_address_prefix]
  # notice that private endpoints do not adhere to NSG rules
  private_endpoint_network_policies             = "Disabled"
  private_link_service_network_policies_enabled = true

  delegation {
    name = "delegation"

    service_delegation {
      name    = "Microsoft.Web/serverFarms"
      actions = ["Microsoft.Network/virtualNetworks/subnets/action"]
    }
  }

  depends_on = [
    # meant to resolve AnotherOperation errors with one operation in the vnet at a time
    azurerm_subnet.services
  ]
}

resource "azurerm_virtual_network_peering" "ws_core_peer" {
  name                      = "ws-core-peer-${local.workspace_resource_name_suffix}"
  resource_group_name       = var.ws_resource_group_name
  virtual_network_name      = azurerm_virtual_network.ws.name
  remote_virtual_network_id = data.azurerm_virtual_network.core.id

  triggers = {
    remote_address_space = join(",", data.azurerm_virtual_network.core.address_space)
  }

  # meant to resolve AnotherOperation errors with one operation in the vnet at a time
  depends_on = [
    azurerm_subnet.webapps
  ]
}

moved {
  from = azurerm_virtual_network_peering.ws-core-peer
  to   = azurerm_virtual_network_peering.ws_core_peer
}

resource "azurerm_virtual_network_peering" "core_ws_peer" {
  provider                  = azurerm.core
  name                      = "core-ws-peer-${local.workspace_resource_name_suffix}"
  resource_group_name       = local.core_resource_group_name
  virtual_network_name      = local.core_vnet
  remote_virtual_network_id = azurerm_virtual_network.ws.id

  triggers = {
    remote_address_space = join(",", azurerm_virtual_network.ws.address_space)
  }

  # meant to resolve AnotherOperation errors with one operation in the vnet at a time
  depends_on = [
    azurerm_virtual_network_peering.ws_core_peer
  ]

}

moved {
  from = azurerm_virtual_network_peering.core-ws-peer
  to   = azurerm_virtual_network_peering.core_ws_peer
}

# If the workspace is deployed to a different subscription to the core,
# it cannot reuse the route table defined in the core, so we need to
# create a new one.
resource "azurerm_route_table" "rt" {
  count                         = local.is_separate_subscription ? 1 : 0
  name                          = local.route_table_name
  location                      = var.location
  resource_group_name           = var.ws_resource_group_name
  bgp_route_propagation_enabled = true

  lifecycle { ignore_changes = [tags] }

  route {
    name                   = "to-firewall"
    address_prefix         = "0.0.0.0/0"
    next_hop_type          = "VirtualAppliance"
    next_hop_in_ip_address = data.azurerm_firewall.firewall.ip_configuration[0].private_ip_address
  }
}

resource "azurerm_subnet_route_table_association" "rt_services_subnet_association" {
  route_table_id = local.route_table_id
  subnet_id      = azurerm_subnet.services.id
  depends_on = [
    # meant to resolve AnotherOperation errors with one operation in the vnet at a time
    azurerm_virtual_network_peering.core_ws_peer
  ]
}


resource "azurerm_subnet_route_table_association" "rt_webapps_subnet_association" {
  route_table_id = local.route_table_id
  subnet_id      = azurerm_subnet.webapps.id
  depends_on = [
    # meant to resolve AnotherOperation errors with one operation in the vnet at a time
    azurerm_subnet_route_table_association.rt_services_subnet_association
  ]
}

module "terraform_azurerm_environment_configuration" {
  source          = "git::https://github.com/microsoft/terraform-azurerm-environment-configuration.git?ref=0.6.0"
  arm_environment = var.arm_environment
}

# Link the workspace network to the DNS Security Policy defined in the core resource group.
resource "azapi_resource" "dns_policy_vnet_link" {
  count     = var.enable_dns_policy ? 1 : 0
  type      = "Microsoft.Network/dnsResolverPolicies/virtualNetworkLinks@2023-07-01-preview"
  parent_id = "${data.azurerm_resource_group.core.id}/providers/Microsoft.Network/dnsResolverPolicies/${local.dns_policy_name}"
  name      = azurerm_virtual_network.ws.name
  location  = var.location
  body = {
    properties = {
      virtualNetwork = {
        id = azurerm_virtual_network.ws.id
      }
    }
  }
}
