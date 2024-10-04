provider "azurerm" {
  features {}

  storage_use_azuread = true
}

locals {
  mgmt_tags = {
    tre_id = var.tre_id
  }
}

# Resource group for TRE core management
resource "azurerm_resource_group" "mgmt" {
  name     = var.mgmt_resource_group_name
  location = var.location

  tags = coalesce(
    {
      project = "Azure Trusted Research Environment"
      source  = "https://github.com/microsoft/AzureTRE/"
    },
    local.mgmt_tags
  )

  lifecycle { ignore_changes = [tags] }
}

# Holds Terraform shared state (already exists, created by bootstrap.sh)
resource "azurerm_storage_account" "state_storage" {
  name                            = var.mgmt_storage_account_name
  resource_group_name             = azurerm_resource_group.mgmt.name
  location                        = azurerm_resource_group.mgmt.location
  account_tier                    = "Standard"
  account_kind                    = "StorageV2"
  account_replication_type        = "LRS"
  allow_nested_items_to_be_public = false
  shared_access_key_enabled       = false
  tags                            = local.mgmt_tags

  lifecycle { ignore_changes = [tags] }
}

# Shared container registry
resource "azurerm_container_registry" "shared_acr" {
  name                = var.acr_name
  resource_group_name = azurerm_resource_group.mgmt.name
  location            = azurerm_resource_group.mgmt.location
  sku                 = var.acr_sku
  admin_enabled       = true
  tags                = local.mgmt_tags

  lifecycle { ignore_changes = [tags] }
}


# tredev is the devcontainer image name generate by our CICD
resource "azurerm_container_registry_task" "tredev_purge" {
  name                  = "tredev_purge"
  container_registry_id = azurerm_container_registry.shared_acr.id
  tags                  = local.mgmt_tags
  platform {
    os           = "Linux"
    architecture = "amd64"
  }
  encoded_step {
    task_content = <<EOF
version: v1.1.0
steps:
  - cmd: acr purge   --filter 'tredev:[0-9a-fA-F]{8}'   --ago 7d --untagged
    disableWorkingDirectoryOverride: true
    timeout: 600
EOF
  }

  timer_trigger {
    name     = "t1"
    schedule = "4 1 * * *"
    enabled  = true
  }
}
