# Key Vault for AI Foundry
# Dedicated Key Vault for AI Foundry secrets (separate from workspace KV which has sensitive credentials)

resource "azurerm_key_vault" "ai_foundry" {
  name                          = local.key_vault_name
  location                      = data.azurerm_resource_group.ws.location
  resource_group_name           = data.azurerm_resource_group.ws.name
  tenant_id                     = data.azurerm_client_config.current.tenant_id
  sku_name                      = "standard"
  purge_protection_enabled      = false
  soft_delete_retention_days    = 7
  public_network_access_enabled = var.is_exposed_externally
  rbac_authorization_enabled    = true

  network_acls {
    bypass         = "AzureServices"
    default_action = var.is_exposed_externally ? "Allow" : "Deny"
  }

  tags = local.workspace_service_tags

  lifecycle {
    ignore_changes = [tags]
  }
}

# Private endpoint for Key Vault
resource "azurerm_private_endpoint" "keyvault" {
  count = var.is_exposed_externally ? 0 : 1

  name                = "pe-${azurerm_key_vault.ai_foundry.name}"
  location            = data.azurerm_resource_group.ws.location
  resource_group_name = data.azurerm_resource_group.ws.name
  subnet_id           = data.azurerm_subnet.services.id
  tags                = local.workspace_service_tags

  private_service_connection {
    name                           = "psc-${azurerm_key_vault.ai_foundry.name}"
    private_connection_resource_id = azurerm_key_vault.ai_foundry.id
    is_manual_connection           = false
    subresource_names              = ["vault"]
  }

  private_dns_zone_group {
    name                 = "dns-${azurerm_key_vault.ai_foundry.name}"
    private_dns_zone_ids = [data.azurerm_private_dns_zone.keyvault.id]
  }

  lifecycle {
    ignore_changes = [tags]
  }
}

# Role assignment for AI Foundry to access Key Vault
resource "azurerm_role_assignment" "ai_foundry_kv_secrets_officer" {
  scope                = azurerm_key_vault.ai_foundry.id
  role_definition_name = "Key Vault Secrets Officer"
  principal_id         = azurerm_cognitive_account.ai_foundry.identity[0].principal_id
}

# Data source for current client config
data "azurerm_client_config" "current" {}
