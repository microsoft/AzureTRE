resource "azurerm_key_vault" "kv" {
  name                      = local.keyvault_name
  location                  = azurerm_resource_group.ws.location
  resource_group_name       = azurerm_resource_group.ws.name
  sku_name                  = "standard"
  enable_rbac_authorization = true
  purge_protection_enabled  = true
  tenant_id                 = data.azurerm_client_config.core.tenant_id
  tags                      = local.tre_workspace_tags

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
  tags                = local.tre_workspace_tags

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

resource "azurerm_monitor_diagnostic_setting" "kv" {
  name                       = "diag-${local.keyvault_name}"
  target_resource_id         = azurerm_key_vault.kv.id
  log_analytics_workspace_id = module.azure_monitor.log_analytics_workspace_id

  dynamic "enabled_log" {
    for_each = ["AuditEvent", "AzurePolicyEvaluationDetails"]
    content {
      category = enabled_log.value
    }
  }

  metric {
    category = "AllMetrics"
    enabled  = true
  }
}

resource "azurerm_role_assignment" "keyvault_resourceprocessor_ws_role" {
  scope                = azurerm_key_vault.kv.id
  role_definition_name = "Key Vault Administrator"
  principal_id         = data.azurerm_user_assigned_identity.resource_processor_vmss_id.principal_id


}

# If running the terraform locally
resource "azurerm_role_assignment" "keyvault_deployer_ws_role" {
  count                = var.enable_local_debugging ? 1 : 0
  scope                = azurerm_key_vault.kv.id
  role_definition_name = "Key Vault Administrator"
  principal_id         = data.azurerm_client_config.core.object_id
}

resource "terraform_data" "wait_for_dns_vault" {
  provisioner "local-exec" {
    command    = "bash -c \"sleep 120s\""
    on_failure = fail
  }

  triggers_replace = [
    azurerm_private_endpoint.kvpe.private_service_connection[0].private_ip_address # only wait on new/changed private IP address
  ]

  depends_on = [azurerm_private_endpoint.kvpe]

}

resource "azurerm_key_vault_secret" "aad_tenant_id" {
  name         = "auth-tenant-id"
  value        = var.auth_tenant_id
  key_vault_id = azurerm_key_vault.kv.id
  tags         = local.tre_workspace_tags
  depends_on = [
    azurerm_role_assignment.keyvault_deployer_ws_role,
    azurerm_role_assignment.keyvault_resourceprocessor_ws_role,
    terraform_data.wait_for_dns_vault
  ]

  lifecycle { ignore_changes = [tags] }
}

# This secret only gets written if Terraform is not responsible for
# registering the AAD Application
resource "azurerm_key_vault_secret" "client_id" {
  name         = "workspace-client-id"
  value        = var.client_id
  key_vault_id = azurerm_key_vault.kv.id
  count        = var.register_aad_application ? 0 : 1
  tags         = local.tre_workspace_tags
  depends_on = [
    azurerm_role_assignment.keyvault_deployer_ws_role,
    azurerm_role_assignment.keyvault_resourceprocessor_ws_role,
    terraform_data.wait_for_dns_vault
  ]

  lifecycle { ignore_changes = [tags] }
}

data "azurerm_key_vault_secret" "client_secret" {
  count        = var.client_secret == local.redacted_senstive_value ? 1 : 0
  name         = "workspace-client-secret"
  key_vault_id = azurerm_key_vault.kv.id
}

# This secret only gets written if Terraform is not responsible for
# registering the AAD Application
resource "azurerm_key_vault_secret" "client_secret" {
  name         = "workspace-client-secret"
  value        = var.client_secret == local.redacted_senstive_value ? data.azurerm_key_vault_secret.client_secret[0].value : var.client_secret
  key_vault_id = azurerm_key_vault.kv.id
  count        = var.register_aad_application ? 0 : 1
  tags         = local.tre_workspace_tags
  depends_on = [
    azurerm_role_assignment.keyvault_deployer_ws_role,
    azurerm_role_assignment.keyvault_resourceprocessor_ws_role,
    terraform_data.wait_for_dns_vault
  ]

  lifecycle { ignore_changes = [tags] }
}
