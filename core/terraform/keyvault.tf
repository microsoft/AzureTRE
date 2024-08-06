resource "azurerm_key_vault" "kv" {
  name                     = "kv-${var.tre_id}"
  tenant_id                = data.azurerm_client_config.current.tenant_id
  location                 = azurerm_resource_group.core.location
  resource_group_name      = azurerm_resource_group.core.name
  sku_name                 = "standard"
  purge_protection_enabled = true
  tags                     = local.tre_core_tags

  lifecycle { ignore_changes = [access_policy, tags] }
}

resource "azurerm_key_vault_access_policy" "deployer" {
  key_vault_id = azurerm_key_vault.kv.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = data.azurerm_client_config.current.object_id

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
  tags                = local.tre_core_tags

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

resource "azurerm_key_vault_secret" "api_client_id" {
  name         = "api-client-id"
  value        = var.api_client_id
  key_vault_id = azurerm_key_vault.kv.id
  tags         = local.tre_core_tags
  depends_on = [
    azurerm_key_vault_access_policy.deployer
  ]
}

resource "azurerm_key_vault_secret" "api_client_secret" {
  name         = "api-client-secret"
  value        = var.api_client_secret
  key_vault_id = azurerm_key_vault.kv.id
  tags         = local.tre_core_tags
  depends_on = [
    azurerm_key_vault_access_policy.deployer
  ]
}

resource "azurerm_key_vault_secret" "auth_tenant_id" {
  name         = "auth-tenant-id"
  value        = var.aad_tenant_id
  key_vault_id = azurerm_key_vault.kv.id
  tags         = local.tre_core_tags
  depends_on = [
    azurerm_key_vault_access_policy.deployer
  ]
}

resource "azurerm_key_vault_secret" "application_admin_client_id" {
  name         = "application-admin-client-id"
  value        = var.application_admin_client_id
  key_vault_id = azurerm_key_vault.kv.id
  tags         = local.tre_core_tags
  depends_on = [
    azurerm_key_vault_access_policy.deployer
  ]
}

resource "azurerm_key_vault_secret" "application_admin_client_secret" {
  name         = "application-admin-client-secret"
  value        = var.application_admin_client_secret
  key_vault_id = azurerm_key_vault.kv.id
  tags         = local.tre_core_tags
  depends_on = [
    azurerm_key_vault_access_policy.deployer
  ]
}

resource "azurerm_key_vault_secret" "notify_uk_template_id" {
  name         = "notify-uk-template-id"
  value        = ""
  key_vault_id = azurerm_key_vault.kv.id
  tags         = local.tre_core_tags
  depends_on = [
    azurerm_key_vault_access_policy.deployer
  ]

  lifecycle { ignore_changes = [ value ] }
}

resource "azurerm_key_vault_secret" "notify_uk_url" {
  name         = "notify-uk-url"
  value        = ""
  key_vault_id = azurerm_key_vault.kv.id
  tags         = local.tre_core_tags
  depends_on = [
    azurerm_key_vault_access_policy.deployer
  ]

  lifecycle { ignore_changes = [ value ] }
}

resource "azurerm_key_vault_secret" "notify_uk_secret" {
  name         = "notify-uk-secret"
  value        = ""
  key_vault_id = azurerm_key_vault.kv.id
  tags         = local.tre_core_tags
  depends_on = [
    azurerm_key_vault_access_policy.deployer
  ]

  lifecycle { ignore_changes = [ value ] }
}

resource "azurerm_key_vault_secret" "notify_uk_iss_id" {
  name         = "notify-uk-iss-id"
  value        = ""
  key_vault_id = azurerm_key_vault.kv.id
  tags         = local.tre_core_tags
  depends_on = [
    azurerm_key_vault_access_policy.deployer
  ]

  lifecycle { ignore_changes = [ value ] }
}

resource "azurerm_key_vault_secret" "notify_uk_email_subject_tag" {
  name         = "notify-uk-email-subject-tag"
  value        = ""
  key_vault_id = azurerm_key_vault.kv.id
  tags         = local.tre_core_tags
  depends_on = [
    azurerm_key_vault_access_policy.deployer
  ]

  lifecycle { ignore_changes = [ value ] }
}

resource "azurerm_monitor_diagnostic_setting" "kv" {
  name                       = "diagnostics-kv-${var.tre_id}"
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

  lifecycle { ignore_changes = [log_analytics_destination_type] }
}
