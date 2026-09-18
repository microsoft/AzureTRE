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
    time = {
      source  = "hashicorp/time"
      version = "~> 0.13"
    }
  }

  backend "azurerm" {}
}

provider "azurerm" {
  features {
    cognitive_account {
      purge_soft_delete_on_destroy = false
    }
    key_vault {
      purge_soft_deleted_secrets_on_destroy = false
      recover_soft_deleted_secrets          = true
    }
  }
}

provider "azapi" {}

module "terraform_azurerm_environment_configuration" {
  source          = "git::https://github.com/microsoft/terraform-azurerm-environment-configuration.git?ref=0.7.0"
  arm_environment = var.arm_environment
}

data "azurerm_client_config" "current" {}

# Read the existing workspace resources.
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

# Read the private DNS zone names from the environment configuration module.
# This keeps the names correct in each Azure cloud.
data "azurerm_private_dns_zone" "cognitive_services" {
  name                = module.terraform_azurerm_environment_configuration.private_links["privatelink.cognitiveservices.azure.com"]
  resource_group_name = local.core_resource_group_name
}

data "azurerm_private_dns_zone" "openai" {
  name                = module.terraform_azurerm_environment_configuration.private_links["privatelink.openai.azure.com"]
  resource_group_name = local.core_resource_group_name
}

# The environment configuration module does not include this zone. Use the same
# explicit name as the core configuration.
data "azurerm_private_dns_zone" "ai_services" {
  name                = "privatelink.services.ai.azure.com"
  resource_group_name = local.core_resource_group_name
}
