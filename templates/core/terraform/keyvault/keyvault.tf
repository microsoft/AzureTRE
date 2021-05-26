resource "azurerm_key_vault" "kv" {
  name                = "kv-${var.resource_name_prefix}-${var.environment}-${var.tre_id}"
  location            = var.location
  resource_group_name = var.resource_group_name
  sku_name            = "standard"
  purge_protection_enabled = true
  tenant_id           = var.tenant_id
}

data "azurerm_client_config" "deployer" {}

resource "azurerm_key_vault_access_policy" "deploy_user" {
  key_vault_id = azurerm_key_vault.kv.id
  tenant_id    = data.azurerm_client_config.deployer.tenant_id
  object_id    = data.azurerm_client_config.deployer.object_id

  key_permissions = [ "Get", "List", "Update", "Create", "Import", "Delete" ]
  secret_permissions = [ "Get", "List", "Set", "Delete" ]
  certificate_permissions = [ "Get", "List", "Update", "Create", "Import", "Delete" ]
}

resource "azurerm_private_dns_zone" "vaultcore" {
  name                = "privatelink.vaultcore.azure.net"
  resource_group_name = var.resource_group_name
}

resource "azurerm_private_dns_zone_virtual_network_link" "vaultcorelink" {
  name                  = "vaultcorelink"
  resource_group_name   = var.resource_group_name
  private_dns_zone_name = azurerm_private_dns_zone.vaultcore.name
  virtual_network_id    = var.core_vnet
}

resource "azurerm_private_endpoint" "kvpe" {
  name                = "pe-kv-${var.resource_name_prefix}-${var.environment}-${var.tre_id}"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.shared_subnet

  private_dns_zone_group {
    name                 = "private-dns-zone-group"
    private_dns_zone_ids = [azurerm_private_dns_zone.vaultcore.id]
  }

  private_service_connection {
    name                           = "psc-kv-${var.resource_name_prefix}-${var.environment}-${var.tre_id}"
    private_connection_resource_id = azurerm_key_vault.kv.id
    is_manual_connection           = false
    subresource_names              = ["Vault"]
  }
}