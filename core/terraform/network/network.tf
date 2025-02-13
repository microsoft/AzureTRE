resource "azurerm_virtual_network" "core" {
  name                = "vnet-${var.tre_id}"
  location            = var.location
  resource_group_name = var.resource_group_name
  address_space       = [var.core_address_space]
  tags                = local.tre_core_tags
  lifecycle { ignore_changes = [tags] }

  subnet {
    name             = "AzureBastionSubnet"
    address_prefixes = [local.bastion_subnet_address_prefix]
    security_group   = azurerm_network_security_group.bastion.id
  }

  subnet {
    name             = "AzureFirewallSubnet"
    address_prefixes = [local.firewall_subnet_address_space]
  }

  subnet {
    name                                          = "AppGwSubnet"
    address_prefixes                              = [local.app_gw_subnet_address_prefix]
    private_endpoint_network_policies             = "Disabled"
    private_link_service_network_policies_enabled = true
    security_group                                = azurerm_network_security_group.app_gw.id
  }

  subnet {
    name                                          = "WebAppSubnet"
    address_prefixes                              = [local.web_app_subnet_address_prefix]
    private_endpoint_network_policies             = "Disabled"
    private_link_service_network_policies_enabled = true
    security_group                                = azurerm_network_security_group.default_rules.id

    delegation {
      name = "delegation"

      service_delegation {
        name    = "Microsoft.Web/serverFarms"
        actions = ["Microsoft.Network/virtualNetworks/subnets/action"]
      }
    }
  }

  subnet {
    name                              = "SharedSubnet"
    address_prefixes                  = [local.shared_services_subnet_address_prefix]
    private_endpoint_network_policies = "Disabled"
    security_group                    = azurerm_network_security_group.default_rules.id
  }

  subnet {
    name                              = "ResourceProcessorSubnet"
    address_prefixes                  = [local.resource_processor_subnet_address_prefix]
    private_endpoint_network_policies = "Disabled"
    security_group                    = azurerm_network_security_group.default_rules.id
  }

  subnet {
    name                              = "AirlockProcessorSubnet"
    address_prefixes                  = [local.airlock_processor_subnet_address_prefix]
    private_endpoint_network_policies = "Disabled"
    security_group                    = azurerm_network_security_group.default_rules.id

    delegation {
      name = "delegation"

      service_delegation {
        name    = "Microsoft.Web/serverFarms"
        actions = ["Microsoft.Network/virtualNetworks/subnets/action"]
      }
    }

    service_endpoints = ["Microsoft.Storage"]
  }

  subnet {
    name                              = "AirlockNotifiactionSubnet"
    address_prefixes                  = [local.airlock_notifications_subnet_address_prefix]
    private_endpoint_network_policies = "Disabled"
    security_group                    = azurerm_network_security_group.default_rules.id

    delegation {
      name = "delegation"

      service_delegation {
        name    = "Microsoft.Web/serverFarms"
        actions = ["Microsoft.Network/virtualNetworks/subnets/action"]
      }
    }
    service_endpoints = ["Microsoft.ServiceBus"]
  }

  subnet {
    name                              = "AirlockStorageSubnet"
    address_prefixes                  = [local.airlock_storage_subnet_address_prefix]
    private_endpoint_network_policies = "Disabled"
    security_group                    = azurerm_network_security_group.default_rules.id
  }

  subnet {
    name                              = "AirlockEventsSubnet"
    address_prefixes                  = [local.airlock_events_subnet_address_prefix]
    private_endpoint_network_policies = "Disabled"
    security_group                    = azurerm_network_security_group.default_rules.id

    service_endpoints = ["Microsoft.ServiceBus"]
  }

  subnet {
    name             = "AzureFirewallManagementSubnet"
    address_prefixes = [local.firewall_management_subnet_address_prefix]
  }
}

resource "azurerm_ip_group" "resource_processor" {
  name                = "ipg-resource-processor"
  location            = var.location
  resource_group_name = var.resource_group_name
  cidrs               = [local.resource_processor_subnet_address_prefix]
  tags                = local.tre_core_tags
  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_ip_group" "shared" {
  name                = "ipg-shared"
  location            = var.location
  resource_group_name = var.resource_group_name
  cidrs               = [local.shared_services_subnet_address_prefix]
  tags                = local.tre_core_tags
  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_ip_group" "webapp" {
  name                = "ipg-web-app"
  location            = var.location
  resource_group_name = var.resource_group_name
  cidrs               = [local.web_app_subnet_address_prefix]
  tags                = local.tre_core_tags
  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_ip_group" "airlock_processor" {
  name                = "ipg-airlock-processor"
  location            = var.location
  resource_group_name = var.resource_group_name
  cidrs               = [local.airlock_processor_subnet_address_prefix]
  tags                = local.tre_core_tags
  lifecycle { ignore_changes = [tags] }
}

module "terraform_azurerm_environment_configuration" {
  source          = "git::https://github.com/microsoft/terraform-azurerm-environment-configuration.git?ref=0.2.0"
  arm_environment = var.arm_environment
}
