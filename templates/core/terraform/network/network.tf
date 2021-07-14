resource "azurerm_virtual_network" "core" {
  name                = "vnet-${var.tre_id}"
  location            = var.location
  resource_group_name = var.resource_group_name
  address_space       = [var.address_space]

  lifecycle { ignore_changes = [ tags ] }
}

resource "azurerm_subnet" "bastion" {
  name                 = "AzureBastionSubnet"
  virtual_network_name = azurerm_virtual_network.core.name
  resource_group_name  = var.resource_group_name
  address_prefixes     = [local.bastion_subnet_address_prefix]
}

resource "azurerm_subnet" "azure_firewall" {
  name                 = "AzureFirewallSubnet"
  virtual_network_name = azurerm_virtual_network.core.name
  resource_group_name  = var.resource_group_name
  address_prefixes     = [local.firewall_subnet_address_space]
}

resource "azurerm_subnet" "app_gw" {
  name                 = "AppGwSubnet"
  virtual_network_name = azurerm_virtual_network.core.name
  resource_group_name  = var.resource_group_name
  address_prefixes     = [local.app_gw_subnet_address_prefix]
}

resource "azurerm_subnet" "web_app" {
  name                                           = "WebAppSubnet"
  virtual_network_name                           = azurerm_virtual_network.core.name
  resource_group_name                            = var.resource_group_name
  address_prefixes                               = [local.web_app_subnet_address_prefix]
  enforce_private_link_endpoint_network_policies = true
  enforce_private_link_service_network_policies  = true

  delegation {
    name = "delegation"

    service_delegation {
      name    = "Microsoft.Web/serverFarms"
      actions = ["Microsoft.Network/virtualNetworks/subnets/action"]
    }
  }
}

resource "azurerm_subnet" "aci" {
  name                                           = "AciSubnet"
  virtual_network_name                           = azurerm_virtual_network.core.name
  resource_group_name                            = var.resource_group_name
  address_prefixes                               = [local.aci_subnet_address_prefix]
  enforce_private_link_endpoint_network_policies = true
  enforce_private_link_service_network_policies  = true

  delegation {
    name = "acidelegationservice"

    service_delegation {
      name    = "Microsoft.ContainerInstance/containerGroups"
      actions = ["Microsoft.Network/virtualNetworks/subnets/action"]
    }
  }
}

resource "azurerm_network_profile" "aciprofile" {
  name                = "aciprofile"
  location            = var.location
  resource_group_name = var.resource_group_name

  container_network_interface {
    name = "acr-frontal-nic"

    ip_configuration {
      name      = "acrfrontal"
      subnet_id = azurerm_subnet.aci.id
    }
  }

  lifecycle { ignore_changes = [ tags ] }
}

resource "azurerm_subnet" "shared" {
  name                                           = "SharedSubnet"
  virtual_network_name                           = azurerm_virtual_network.core.name
  resource_group_name                            = var.resource_group_name
  address_prefixes                               = [local.shared_services_subnet_address_prefix]
  # notice that private endpoints do not adhere to NSG rules
  enforce_private_link_endpoint_network_policies = true
}


resource "azurerm_subnet" "resource_processor" {
  name                                           = "ResourceProcessorSubnet"
  virtual_network_name                           = azurerm_virtual_network.core.name
  resource_group_name                            = var.resource_group_name
  address_prefixes                               = [local.resource_processor_subnet_address_prefix]
  # notice that private endpoints do not adhere to NSG rules
  enforce_private_link_endpoint_network_policies = true
}
