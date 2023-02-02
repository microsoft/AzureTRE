data "azurerm_client_config" "current" {}

resource "azurerm_key_vault" "kv" {
  name                     = local.keyvault_name
  location                 = azurerm_resource_group.ws.location
  resource_group_name      = azurerm_resource_group.ws.name
  sku_name                 = "standard"
  purge_protection_enabled = true
  tenant_id                = data.azurerm_client_config.current.tenant_id
  tags                     = local.tre_workspace_tags

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

      retention_policy {
        enabled = true
        days    = 365
      }
    }
  }

  metric {
    category = "AllMetrics"
    enabled  = true

    retention_policy {
      enabled = true
      days    = 365
    }
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

  secret_permissions = ["Get", "List", "Set", "Delete", "Purge", "Recover"]
}

# If running the terraform locally
resource "azurerm_key_vault_access_policy" "deployer" {
  count        = var.enable_local_debugging ? 1 : 0
  key_vault_id = azurerm_key_vault.kv.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = data.azurerm_client_config.current.object_id

  secret_permissions = ["Get", "List", "Set", "Delete", "Purge", "Recover"]
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
  tags         = local.tre_workspace_tags
  depends_on = [
    azurerm_key_vault_access_policy.deployer,
    azurerm_key_vault_access_policy.resource_processor,
    null_resource.wait_for_dns_vault
  ]
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
    azurerm_key_vault_access_policy.deployer,
    azurerm_key_vault_access_policy.resource_processor,
    null_resource.wait_for_dns_vault
  ]
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
    azurerm_key_vault_access_policy.deployer,
    azurerm_key_vault_access_policy.resource_processor,
    null_resource.wait_for_dns_vault
  ]
}
