resource "azurerm_key_vault" "kv" {
  name                     = local.keyvault_name
  location                 = azurerm_resource_group.ws.location
  resource_group_name      = azurerm_resource_group.ws.name
  sku_name                 = "standard"
  purge_protection_enabled = true
  tenant_id                = data.azurerm_client_config.current.tenant_id

  network_acls {
    bypass         = "AzureServices"
    default_action = var.enable_local_debugging ? "Allow" : "Deny"
  }

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_endpoint" "kvpe" {
  name                = "kvpe-${local.workspace_resource_name_suffix}"
  location            = azurerm_resource_group.ws.location
  resource_group_name = azurerm_resource_group.ws.name
  subnet_id           = module.network.services_subnet_id

  depends_on = [
    module.network,
  ]

  lifecycle { ignore_changes = [tags] }

  private_dns_zone_group {
    name                 = "private-dns-zone-group"
    private_dns_zone_ids = [module.network.vaultcore_zone_id]
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

  secret_permissions = ["Get", "List", "Set", "Delete", "Purge"]
}

# If running the terraform locally
resource "azurerm_key_vault_access_policy" "deployer" {
  count        = var.enable_local_debugging ? 1 : 0
  key_vault_id = azurerm_key_vault.kv.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = data.azurerm_client_config.current.object_id

  secret_permissions = ["Get", "List", "Set", "Delete", "Purge"]
}

resource "null_resource" "wait_for_dns_vault" {
  provisioner "local-exec" {
    command    = "bash -c \"sleep 120s\""
    on_failure = fail
  }

  triggers = {
    always_run = azurerm_private_endpoint.kvpe.private_service_connection[0].private_ip_address # only wait on new/changed private IP address
  }

  depends_on = [azurerm_private_endpoint.kvpe]
}

resource "azurerm_key_vault_secret" "aad_tenant_id" {
  name         = "auth-tenant-id"
  value        = var.auth_tenant_id
  key_vault_id = azurerm_key_vault.kv.id
  depends_on = [
    azurerm_key_vault_access_policy.deployer,
    azurerm_key_vault_access_policy.resource_processor,
    null_resource.wait_for_dns_vault
  ]
}
