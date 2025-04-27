resource "azurerm_key_vault" "kv" {
  name                      = local.kv_name
  tenant_id                 = data.azurerm_client_config.current.tenant_id
  location                  = azurerm_resource_group.core.location
  resource_group_name       = azurerm_resource_group.core.name
  sku_name                  = "standard"
  enable_rbac_authorization = true
  purge_protection_enabled  = var.kv_purge_protection_enabled
  tags                      = local.tre_core_tags

  public_network_access_enabled = local.kv_public_network_access_enabled

  network_acls {
    default_action             = local.kv_network_default_action
    bypass                     = local.kv_network_bypass
    virtual_network_subnet_ids = compact([local.private_agent_subnet_id])
  }

  lifecycle {
    ignore_changes = [access_policy, tags]
  }

  # create provisioner required due to https://github.com/hashicorp/terraform-provider-azurerm/issues/18970
  #
  provisioner "local-exec" {
    when    = create
    command = <<EOT
az keyvault update --name ${local.kv_name} --public-network-access ${local.kv_public_network_access_enabled ? "Enabled" : "Disabled"} --default-action ${local.kv_network_default_action} --bypass "${local.kv_network_bypass}" --output none
${local.private_agent_subnet_id != "" ? "az keyvault network-rule add --name ${local.kv_name} --subnet ${local.private_agent_subnet_id} --output none" : ""}
EOT
  }
}

resource "azurerm_role_assignment" "keyvault_deployer_role" {
  scope                = azurerm_key_vault.kv.id
  role_definition_name = "Key Vault Administrator"
  principal_id         = data.azurerm_client_config.current.object_id // deployer - either CICD service principal or local user
}

resource "azurerm_role_assignment" "keyvault_apiidentity_role" {
  scope                = azurerm_key_vault.kv.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.id.principal_id // id-api-<TRE_ID>
}

data "azurerm_private_dns_zone" "vaultcore" {
  name                = module.terraform_azurerm_environment_configuration.private_links["privatelink.vaultcore.azure.net"]
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
    azurerm_role_assignment.keyvault_deployer_role
  ]

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_key_vault_secret" "api_client_secret" {
  name         = "api-client-secret"
  value        = var.api_client_secret
  key_vault_id = azurerm_key_vault.kv.id
  tags         = local.tre_core_tags
  depends_on = [
    azurerm_role_assignment.keyvault_deployer_role
  ]

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_key_vault_secret" "auth_tenant_id" {
  name         = "auth-tenant-id"
  value        = var.aad_tenant_id
  key_vault_id = azurerm_key_vault.kv.id
  tags         = local.tre_core_tags
  depends_on = [
    azurerm_role_assignment.keyvault_deployer_role
  ]

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_key_vault_secret" "application_admin_client_id" {
  name         = "application-admin-client-id"
  value        = var.application_admin_client_id
  key_vault_id = azurerm_key_vault.kv.id
  tags         = local.tre_core_tags
  depends_on = [
    azurerm_role_assignment.keyvault_deployer_role
  ]

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_key_vault_secret" "application_admin_client_secret" {
  name         = "application-admin-client-secret"
  value        = var.application_admin_client_secret
  key_vault_id = azurerm_key_vault.kv.id
  tags         = local.tre_core_tags
  depends_on = [
    azurerm_role_assignment.keyvault_deployer_role
  ]

  lifecycle { ignore_changes = [tags] }
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
