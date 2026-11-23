# Inbound rules for the CycleCloud server. The outbound rules stay at the Azure defaults.
resource "azurerm_network_security_group" "cyclecloud" {
  name                = "nsg-cyclecloud-${var.tre_id}-${local.short_service_id}"
  location            = data.azurerm_resource_group.rg.location
  resource_group_name = local.core_resource_group_name
  tags                = local.tre_shared_service_tags

  # The admin jumpbox and Azure Bastion are in the core virtual network.
  security_rule {
    name                       = "AllowCoreHttpsSshInbound"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_ranges    = ["22", "443"]
    source_address_prefixes    = data.azurerm_virtual_network.core.address_space
    destination_address_prefix = "*"
  }

  # Cluster nodes without a return proxy connect to the CycleCloud server on port 9443.
  dynamic "security_rule" {
    for_each = length(local.cluster_address_spaces) > 0 ? [local.cluster_address_spaces] : []
    content {
      name                       = "AllowClusterNodesInbound"
      priority                   = 110
      direction                  = "Inbound"
      access                     = "Allow"
      protocol                   = "Tcp"
      source_port_range          = "*"
      destination_port_range     = "9443"
      source_address_prefixes    = security_rule.value
      destination_address_prefix = "*"
    }
  }

  security_rule {
    name                       = "AllowAzureLoadBalancerInbound"
    priority                   = 120
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "AzureLoadBalancer"
    destination_address_prefix = "*"
  }

  # Peered workspace networks are part of the VirtualNetwork service tag.
  security_rule {
    name                       = "DenyVirtualNetworkInbound"
    priority                   = 4096
    direction                  = "Inbound"
    access                     = "Deny"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "VirtualNetwork"
    destination_address_prefix = "*"
  }

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_network_interface_security_group_association" "cyclecloud" {
  network_interface_id      = azurerm_network_interface.cyclecloud.id
  network_security_group_id = azurerm_network_security_group.cyclecloud.id
}
