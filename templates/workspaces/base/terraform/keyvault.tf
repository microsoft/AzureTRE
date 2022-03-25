resource "azurerm_key_vault" "kv" {
  name                     = local.keyvault_name
  location                 = azurerm_resource_group.ws.location
  resource_group_name      = azurerm_resource_group.ws.name
  sku_name                 = "standard"
  purge_protection_enabled = true
  tenant_id                = data.azurerm_client_config.current.tenant_id

  network_acls {
    bypass         = "None"
    default_action = "Deny"
  }

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_endpoint" "kvpe" {
  name                = "kvpe-${local.workspace_resource_name_suffix}"
  location            = azurerm_resource_group.ws.location
  resource_group_name = azurerm_resource_group.ws.name
  subnet_id           = azurerm_subnet.services.id

  lifecycle { ignore_changes = [tags] }

  private_dns_zone_group {
    name                 = "private-dns-zone-group"
    private_dns_zone_ids = [data.azurerm_private_dns_zone.vaultcore.id]
  }

  private_service_connection {
    name                           = "kvpescv-${local.workspace_resource_name_suffix}"
    private_connection_resource_id = azurerm_key_vault.kv.id
    is_manual_connection           = false
    subresource_names              = ["Vault"]
  }
}


data "azurerm_user_assigned_identity" "resource_processor_vmss_id" {
  name                = "id-vmss-${var.tre_id}"
  resource_group_name = "rg-${var.tre_id}"
}

resource "azurerm_key_vault_access_policy" "resource_processor" {
  key_vault_id = azurerm_key_vault.kv.id
  tenant_id    = data.azurerm_user_assigned_identity.resource_processor_vmss_id.tenant_id
  object_id    = data.azurerm_user_assigned_identity.resource_processor_vmss_id.principal_id

  secret_permissions = ["Get", "List", "Set", "Delete"]
}
