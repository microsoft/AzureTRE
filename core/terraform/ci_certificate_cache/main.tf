terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "= 4.57.0"
    }
  }
}

resource "azurerm_key_vault" "cache" {
  count                         = var.enabled ? 1 : 0
  name                          = var.vault_name
  location                      = var.location
  resource_group_name           = var.resource_group_name
  tenant_id                     = var.tenant_id
  sku_name                      = "standard"
  rbac_authorization_enabled    = true
  public_network_access_enabled = false
  purge_protection_enabled      = var.purge_protection_enabled
  tags                          = var.tags

  network_acls {
    default_action = "Deny"
    bypass         = "None"
  }
}

resource "azurerm_private_endpoint" "cache" {
  count               = var.enabled ? 1 : 0
  name                = "pe-${var.vault_name}"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.shared_subnet_id
  tags                = var.tags

  private_dns_zone_group {
    name                 = "private-dns-zone-group"
    private_dns_zone_ids = [var.private_dns_zone_id]
  }

  private_service_connection {
    name                           = "psc-${var.vault_name}"
    private_connection_resource_id = azurerm_key_vault.cache[0].id
    is_manual_connection           = false
    subresource_names              = ["Vault"]
  }
}

# The resource processor imports and restores certificates. Core-vault readers
# receive no data-plane role on this vault.
resource "azurerm_role_assignment" "resource_processor_certificates" {
  count                = var.enabled ? 1 : 0
  scope                = azurerm_key_vault.cache[0].id
  role_definition_name = "Key Vault Certificates Officer"
  principal_id         = var.resource_processor_principal_id
}

resource "azurerm_role_assignment" "resource_processor_secrets" {
  count                = var.enabled ? 1 : 0
  scope                = azurerm_key_vault.cache[0].id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = var.resource_processor_principal_id
}

resource "azurerm_role_assignment" "deployer" {
  count                = var.enabled ? 1 : 0
  scope                = azurerm_key_vault.cache[0].id
  role_definition_name = "Key Vault Administrator"
  principal_id         = var.deployer_principal_id
}

resource "azurerm_monitor_diagnostic_setting" "cache" {
  count                      = var.enabled ? 1 : 0
  name                       = "diagnostics-${var.vault_name}"
  target_resource_id         = azurerm_key_vault.cache[0].id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  enabled_log {
    category = "AuditEvent"
  }
}
