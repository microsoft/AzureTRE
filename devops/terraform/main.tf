provider "azurerm" {
  features {}

  storage_use_azuread = true
}

data "azurerm_client_config" "current" {}

# Resource group for TRE core management
resource "azurerm_resource_group" "mgmt" {
  name     = var.mgmt_resource_group_name
  location = var.location

  tags = {
    project = "Azure Trusted Research Environment"
    source  = "https://github.com/microsoft/AzureTRE/"
  }

  lifecycle { ignore_changes = [tags] }
}

# Holds Terraform shared state (already exists, created by bootstrap.sh)
resource "azurerm_storage_account" "state_storage" {
  name                             = var.mgmt_storage_account_name
  resource_group_name              = azurerm_resource_group.mgmt.name
  location                         = azurerm_resource_group.mgmt.location
  account_tier                     = "Standard"
  account_kind                     = "StorageV2"
  account_replication_type         = "LRS"
  table_encryption_key_type        = var.enable_cmk_encryption ? "Account" : "Service"
  queue_encryption_key_type        = var.enable_cmk_encryption ? "Account" : "Service"
  cross_tenant_replication_enabled = false
  allow_nested_items_to_be_public  = false
  shared_access_key_enabled        = false

  dynamic "identity" {
    for_each = var.enable_cmk_encryption ? [1] : []
    content {
      type         = "UserAssigned"
      identity_ids = [azurerm_user_assigned_identity.tre_mgmt_encryption[0].id]
    }
  }

  # changing this value is destructive, hence attribute is in lifecycle.ignore_changes block below
  infrastructure_encryption_enabled = true

  lifecycle { ignore_changes = [infrastructure_encryption_enabled, tags] }
}

resource "azurerm_storage_account_customer_managed_key" "state_storage_encryption" {
  count                     = var.enable_cmk_encryption ? 1 : 0
  storage_account_id        = azurerm_storage_account.state_storage.id
  key_vault_id              = local.key_store_id
  key_name                  = var.kv_mgmt_encryption_key_name
  user_assigned_identity_id = azurerm_user_assigned_identity.tre_mgmt_encryption[0].id

  depends_on = [
    azurerm_role_assignment.kv_mgmt_encryption_key_user,
    azurerm_key_vault_key.tre_mgmt_encryption[0]
  ]
}



# Shared container registry
resource "azurerm_container_registry" "shared_acr" {
  name                = var.acr_name
  resource_group_name = azurerm_resource_group.mgmt.name
  location            = azurerm_resource_group.mgmt.location
  sku                 = var.acr_sku != null ? var.acr_sku : (var.enable_cmk_encryption ? "Premium" : "Standard")
  admin_enabled       = true

  dynamic "identity" {
    for_each = var.enable_cmk_encryption ? [1] : []
    content {
      type         = "UserAssigned"
      identity_ids = [azurerm_user_assigned_identity.tre_mgmt_encryption[0].id]
    }
  }

  dynamic "encryption" {
    for_each = var.enable_cmk_encryption ? [1] : []
    content {
      enabled            = true
      key_vault_key_id   = azurerm_key_vault_key.tre_mgmt_encryption[0].id
      identity_client_id = azurerm_user_assigned_identity.tre_mgmt_encryption[0].client_id
    }

  }

  lifecycle { ignore_changes = [tags] }
}


# tredev is the devcontainer image name generate by our CICD
resource "azurerm_container_registry_task" "tredev_purge" {
  name                  = "tredev_purge"
  container_registry_id = azurerm_container_registry.shared_acr.id
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

# Key Vault for encryption keys
resource "azurerm_key_vault" "encryption_kv" {
  count                       = var.enable_cmk_encryption && var.external_key_store_id == null ? 1 : 0
  name                        = var.encryption_kv_name
  resource_group_name         = azurerm_resource_group.mgmt.name
  location                    = azurerm_resource_group.mgmt.location
  enabled_for_disk_encryption = true
  sku_name                    = "standard"
  tenant_id                   = data.azurerm_client_config.current.tenant_id
  enable_rbac_authorization   = true
  purge_protection_enabled    = true

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_role_assignment" "current_user_to_key_vault_crypto_officer" {
  count                = var.enable_cmk_encryption && var.external_key_store_id == null ? 1 : 0
  scope                = azurerm_key_vault.encryption_kv[0].id
  role_definition_name = "Key Vault Crypto Officer"
  principal_id         = data.azurerm_client_config.current.object_id
}

