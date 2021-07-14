data "azurerm_client_config" "deployer" {}

resource "azurerm_key_vault" "kv" {
  name                     = "kv-${var.tre_id}"
  tenant_id                = var.tenant_id
  location                 = var.location
  resource_group_name      = var.resource_group_name
  sku_name                 = "standard"
  purge_protection_enabled = var.debug == "true" ? false : true
  
  lifecycle { ignore_changes = [ tags ] }
}

resource "azurerm_key_vault_access_policy" "deployer" {
  key_vault_id = azurerm_key_vault.kv.id
  tenant_id    = data.azurerm_client_config.deployer.tenant_id
  object_id    = data.azurerm_client_config.deployer.object_id

  key_permissions         = ["Get", "List", "Update", "Create", "Import", "Delete", ]
  secret_permissions      = ["Get", "List", "Set", "Delete" ]
  certificate_permissions = ["Get", "List", "Update", "Create", "Import", "Delete", "Purge" ]
  storage_permissions     = ["Get", "List", "Update", "Delete" ]
}

resource "azurerm_key_vault_access_policy" "managed_identity" {
  key_vault_id = azurerm_key_vault.kv.id
  tenant_id    = var.managed_identity_tenant_id
  object_id    = var.managed_identity_object_id

  key_permissions         = ["Get", "List", ]
  secret_permissions      = ["Get", "List", ]
  certificate_permissions = ["Get", "List", ]
}

resource "azurerm_private_dns_zone" "vaultcore" {
  name                = "privatelink.vaultcore.azure.net"
  resource_group_name = var.resource_group_name

  lifecycle { ignore_changes = [ tags ] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "vaultcorelink" {
  name                  = "vaultcorelink"
  resource_group_name   = var.resource_group_name
  private_dns_zone_name = azurerm_private_dns_zone.vaultcore.name
  virtual_network_id    = var.core_vnet

  lifecycle { ignore_changes = [ tags ] }
}

resource "azurerm_private_endpoint" "kvpe" {
  name                = "pe-kv-${var.tre_id}"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.shared_subnet

  lifecycle { ignore_changes = [ tags ] }

  private_dns_zone_group {
    name                 = "private-dns-zone-group"
    private_dns_zone_ids = [azurerm_private_dns_zone.vaultcore.id]
  }

  private_service_connection {
    name                           = "psc-kv-${var.tre_id}"
    private_connection_resource_id = azurerm_key_vault.kv.id
    is_manual_connection           = false
    subresource_names              = ["Vault"]
  }
}
