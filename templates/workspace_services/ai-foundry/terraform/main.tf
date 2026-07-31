terraform {
  required_version = ">= 1.9.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.58"
    }
    azapi = {
      source  = "Azure/azapi"
      version = "~> 2.8"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.8"
    }
    time = {
      source  = "hashicorp/time"
      version = "~> 0.13"
    }
  }

  backend "azurerm" {}
}

provider "azurerm" {
  features {}
  # Use Azure AD auth for storage operations (required when shared key access is disabled by policy)
  storage_use_azuread = true
}

provider "azapi" {}

module "terraform_azurerm_environment_configuration" {
  source          = "git::https://github.com/microsoft/terraform-azurerm-environment-configuration.git?ref=0.6.0"
  arm_environment = var.arm_environment
}

# Data sources for workspace resources
data "azurerm_resource_group" "ws" {
  name = "rg-${var.tre_id}-ws-${local.short_workspace_id}"
}

data "azurerm_virtual_network" "ws" {
  name                = "vnet-${var.tre_id}-ws-${local.short_workspace_id}"
  resource_group_name = data.azurerm_resource_group.ws.name
}

data "azurerm_subnet" "services" {
  name                 = "ServicesSubnet"
  virtual_network_name = data.azurerm_virtual_network.ws.name
  resource_group_name  = data.azurerm_resource_group.ws.name
}

# Use the core route table for routing through the firewall
data "azurerm_route_table" "rt" {
  name                = "rt-${var.tre_id}"
  resource_group_name = local.core_resource_group_name
}

# Private DNS zones from core resource group. Zone names are resolved via the
# environment-configuration module so they are correct in non-public clouds.
data "azurerm_private_dns_zone" "cognitive_services" {
  name                = module.terraform_azurerm_environment_configuration.private_links["privatelink.cognitiveservices.azure.com"]
  resource_group_name = local.core_resource_group_name
}

data "azurerm_private_dns_zone" "openai" {
  name                = module.terraform_azurerm_environment_configuration.private_links["privatelink.openai.azure.com"]
  resource_group_name = local.core_resource_group_name
}

# Not yet in the environment-configuration module, so referenced by name (matches core).
data "azurerm_private_dns_zone" "ai_services" {
  name                = "privatelink.services.ai.azure.com"
  resource_group_name = local.core_resource_group_name
}

data "azurerm_private_dns_zone" "blob" {
  name                = module.terraform_azurerm_environment_configuration.private_links["privatelink.blob.core.windows.net"]
  resource_group_name = local.core_resource_group_name
}

data "azurerm_private_dns_zone" "keyvault" {
  name                = module.terraform_azurerm_environment_configuration.private_links["privatelink.vaultcore.azure.net"]
  resource_group_name = local.core_resource_group_name
}

# Not yet in the environment-configuration module, so referenced by name (matches core).
data "azurerm_private_dns_zone" "ai_search" {
  name                = "privatelink.search.windows.net"
  resource_group_name = local.core_resource_group_name
}

data "azurerm_private_dns_zone" "file" {
  name                = module.terraform_azurerm_environment_configuration.private_links["privatelink.file.core.windows.net"]
  resource_group_name = local.core_resource_group_name
}

# Workspace storage account - reuse to avoid quota limits
data "azurerm_storage_account" "workspace" {
  name                = "stgws${local.short_workspace_id}"
  resource_group_name = data.azurerm_resource_group.ws.name
}

data "azurerm_private_dns_zone" "cosmos_db" {
  count               = var.enable_agent_service ? 1 : 0
  name                = module.terraform_azurerm_environment_configuration.private_links["privatelink.documents.azure.com"]
  resource_group_name = local.core_resource_group_name
}
