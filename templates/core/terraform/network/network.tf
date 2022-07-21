resource "azurerm_virtual_network" "core" {
  name                = "vnet-${var.tre_id}"
  location            = var.location
  resource_group_name = var.resource_group_name
  address_space       = [var.core_address_space]
  tags                = local.tre_core_tags
  lifecycle { ignore_changes = [tags] }
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
  name                                           = "AppGwSubnet"
  virtual_network_name                           = azurerm_virtual_network.core.name
  resource_group_name                            = var.resource_group_name
  address_prefixes                               = [local.app_gw_subnet_address_prefix]
  enforce_private_link_endpoint_network_policies = true
  enforce_private_link_service_network_policies  = true
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

resource "azurerm_subnet" "shared" {
  name                 = "SharedSubnet"
  virtual_network_name = azurerm_virtual_network.core.name
  resource_group_name  = var.resource_group_name
  address_prefixes     = [local.shared_services_subnet_address_prefix]
  # notice that private endpoints do not adhere to NSG rules
  enforce_private_link_endpoint_network_policies = true
}

resource "azurerm_subnet" "resource_processor" {
  name                 = "ResourceProcessorSubnet"
  virtual_network_name = azurerm_virtual_network.core.name
  resource_group_name  = var.resource_group_name
  address_prefixes     = [local.resource_processor_subnet_address_prefix]
  # notice that private endpoints do not adhere to NSG rules
  enforce_private_link_endpoint_network_policies = true
}

resource "azurerm_subnet" "airlock_processor" {
  name                 = "AirlockProcessorSubnet"
  virtual_network_name = azurerm_virtual_network.core.name
  resource_group_name  = var.resource_group_name
  address_prefixes     = [local.airlock_processor_subnet_address_prefix]
  # notice that private endpoints do not adhere to NSG rules
  enforce_private_link_endpoint_network_policies = true

  delegation {
    name = "delegation"

    service_delegation {
      name    = "Microsoft.Web/serverFarms"
      actions = ["Microsoft.Network/virtualNetworks/subnets/action"]
    }
  }

  # Todo: needed as we want to open the fw for this subnet in some of the airlock storages (export inprogress)
  # https://github.com/microsoft/AzureTRE/issues/2098
  service_endpoints = ["Microsoft.Storage"]

}

resource "azurerm_subnet" "airlock_notification" {
  name                 = "AirlockNotifiactionSubnet"
  virtual_network_name = azurerm_virtual_network.core.name
  resource_group_name  = var.resource_group_name
  address_prefixes     = [local.airlock_notifications_subnet_address_prefix]
  # notice that private endpoints do not adhere to NSG rules
  enforce_private_link_endpoint_network_policies = true

  delegation {
    name = "delegation"

    service_delegation {
      name    = "Microsoft.Web/serverFarms"
      actions = ["Microsoft.Network/virtualNetworks/subnets/action"]
    }
  }

}

resource "azurerm_subnet" "airlock_storage" {
  name                 = "AirlockStorageSubnet"
  virtual_network_name = azurerm_virtual_network.core.name
  resource_group_name  = var.resource_group_name
  address_prefixes     = [local.airlock_storage_subnet_address_prefix]
  # notice that private endpoints do not adhere to NSG rules
  enforce_private_link_endpoint_network_policies = true
}

resource "azurerm_subnet" "airlock_events" {
  name                 = "AirlockEventsSubnet"
  virtual_network_name = azurerm_virtual_network.core.name
  resource_group_name  = var.resource_group_name
  address_prefixes     = [local.airlock_events_subnet_address_prefix]
  # notice that private endpoints do not adhere to NSG rules
  enforce_private_link_endpoint_network_policies = true

  # Eventgrid CAN'T send messages over private endpoints, hence we need to allow service endpoints to the service bus
  # We are using service endpoints + managed identity to send these messaages
  # https://docs.microsoft.com/en-us/azure/event-grid/consume-private-endpoints
  service_endpoints = ["Microsoft.ServiceBus"]
}
