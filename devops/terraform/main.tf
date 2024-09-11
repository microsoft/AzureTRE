provider "azurerm" {
  features {}
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
  name                            = var.mgmt_storage_account_name
  resource_group_name             = azurerm_resource_group.mgmt.name
  location                        = azurerm_resource_group.mgmt.location
  account_tier                    = "Standard"
  account_kind                    = "StorageV2"
  account_replication_type        = "LRS"
  allow_nested_items_to_be_public = false

  lifecycle { ignore_changes = [tags] }
}

# Shared container registry
resource "azurerm_container_registry" "shared_acr" {
  name                = var.acr_name
  resource_group_name = azurerm_resource_group.mgmt.name
  location            = azurerm_resource_group.mgmt.location
  sku                 = var.acr_sku
  admin_enabled       = true

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
resource "azurerm_key_vault" "shared_kv" {
  count                       = var.enable_cmk_encryption ? 1 : 0
  name                        = var.kv_name
  resource_group_name         = azurerm_resource_group.mgmt.name
  location                    = azurerm_resource_group.mgmt.location
  enabled_for_disk_encryption = true
  sku_name                    = "standard"
  tenant_id                   = data.azurerm_client_config.current.tenant_id
  enable_rbac_authorization   = true

  # Purge protection needs to be enabled for customer managed key encryption
  purge_protection_enabled = true

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_role_assignment" "current_user_to_key_vault_crypto_officer" {
  count                = var.enable_cmk_encryption ? 1 : 0
  scope                = azurerm_key_vault.shared_kv[0].id
  role_definition_name = "Key Vault Crypto Officer"
  principal_id         = data.azurerm_client_config.current.object_id
}

# Key used to encrypt resources
resource "azurerm_key_vault_key" "encryption" {
  count        = var.enable_cmk_encryption ? 1 : 0
  
  name         = var.kv_encryption_key_name
  key_vault_id = azurerm_key_vault.shared_kv[0].id
  key_type     = "RSA"
  key_size     = 2048

  key_opts = [
    "decrypt",
    "encrypt",
    "sign",
    "unwrapKey",
    "verify",
    "wrapKey",
  ]

  depends_on = [
    azurerm_role_assignment.current_user_to_key_vault_crypto_officer
  ]
}

