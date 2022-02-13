data "azurerm_client_config" "deployer" {}

resource "azurerm_key_vault" "kv" {
  name                     = "kv-${var.tre_id}"
  tenant_id                = data.azurerm_client_config.current.tenant_id
  location                 = azurerm_resource_group.core.location
  resource_group_name      = azurerm_resource_group.core.name
  sku_name                 = "standard"
  purge_protection_enabled = var.debug == true ? false : true

  lifecycle { ignore_changes = [access_policy, tags] }
}

resource "azurerm_key_vault_access_policy" "deployer" {
  key_vault_id = azurerm_key_vault.kv.id
  tenant_id    = data.azurerm_client_config.deployer.tenant_id
  object_id    = data.azurerm_client_config.deployer.object_id

  key_permissions         = ["Get", "List", "Update", "Create", "Import", "Delete", "Recover"]
  secret_permissions      = ["Get", "List", "Set", "Delete", "Purge", "Recover"]
  certificate_permissions = ["Get", "List", "Update", "Create", "Import", "Delete", "Purge", "Recover"]
  storage_permissions     = ["Get", "List", "Update", "Delete"]
}

resource "azurerm_key_vault_access_policy" "managed_identity" {
  key_vault_id = azurerm_key_vault.kv.id
  tenant_id    = azurerm_user_assigned_identity.id.tenant_id
  object_id    = azurerm_user_assigned_identity.id.principal_id

  key_permissions         = ["Get", "List", ]
  secret_permissions      = ["Get", "List", ]
  certificate_permissions = ["Get", "List", ]
}

data "azurerm_private_dns_zone" "vaultcore" {
  name                = "privatelink.vaultcore.azure.net"
  resource_group_name = azurerm_resource_group.core.name

  depends_on = [
    module.network,
  ]
}

resource "azurerm_private_endpoint" "kvpe" {
  name                = "pe-kv-${var.tre_id}"
  location            = azurerm_resource_group.core.location
  resource_group_name = azurerm_resource_group.core.name
  subnet_id           = module.network.shared_subnet_id

  lifecycle { ignore_changes = [tags] }

  private_dns_zone_group {
    name                 = "private-dns-zone-group"
    private_dns_zone_ids = [data.azurerm_private_dns_zone.vaultcore.id]
  }

  private_service_connection {
    name                           = "psc-kv-${var.tre_id}"
    private_connection_resource_id = azurerm_key_vault.kv.id
    is_manual_connection           = false
    subresource_names              = ["Vault"]
  }
}
