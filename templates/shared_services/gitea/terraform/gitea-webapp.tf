resource "random_password" "gitea_passwd" {
  length      = 20
  min_upper   = 2
  min_lower   = 2
  min_numeric = 2
  min_special = 2
}

# we have to use user-assigned to break a cycle in the dependencies: app identity, kv-policy, secrets in app settings
resource "azurerm_user_assigned_identity" "gitea_id" {
  resource_group_name = local.core_resource_group_name
  location            = data.azurerm_resource_group.rg.location
  tags                = local.tre_shared_service_tags

  name = "id-gitea-${var.tre_id}"

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_linux_web_app" "gitea" {
  name                                           = local.webapp_name
  resource_group_name                            = local.core_resource_group_name
  location                                       = data.azurerm_resource_group.rg.location
  service_plan_id                                = data.azurerm_service_plan.core.id
  https_only                                     = true
  key_vault_reference_identity_id                = azurerm_user_assigned_identity.gitea_id.id
  virtual_network_subnet_id                      = data.azurerm_subnet.web_app.id
  ftp_publish_basic_authentication_enabled       = false
  webdeploy_publish_basic_authentication_enabled = false
  tags                                           = local.tre_shared_service_tags

  app_settings = {
    WEBSITES_PORT                       = "3000"
    WEBSITES_ENABLE_APP_SERVICE_STORAGE = false

    GITEA_USERNAME = "giteaadmin"
    GITEA_PASSWD   = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.gitea_password.id})"
    GITEA_EMAIL    = "giteaadmin@azuretre.com"

    GITEA__server__ROOT_URL              = "https://${local.webapp_name}.azurewebsites.net/"
    GITEA__server__LFS_START_SERVER      = "true"
    GITEA__lfs__PATH                     = "/data/lfs"
    GITEA__lfs__STORAGE_TYPE             = "local"
    GITEA__log_0x2E_console__COLORIZE    = "false" # Azure monitor doens't show colors, so this is easier to read.
    GITEA__picture__DISABLE_GRAVATAR     = "true"  # external avaters are not available due to network restrictions
    GITEA__security__INSTALL_LOCK        = true
    GITEA__service__DISABLE_REGISTRATION = true

    GITEA__database__SSL_MODE = "true"
    GITEA__database__DB_TYPE  = "mysql"
    GITEA__database__HOST     = azurerm_mysql_flexible_server.gitea.fqdn
    GITEA__database__NAME     = azurerm_mysql_flexible_database.gitea.name
    GITEA__database__USER     = azurerm_mysql_flexible_server.gitea.administrator_login
    GITEA__database__PASSWD   = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.db_password.id})"
  }

  lifecycle { ignore_changes = [tags] }

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.gitea_id.id]
  }

  site_config {
    container_registry_use_managed_identity       = true
    container_registry_managed_identity_client_id = azurerm_user_assigned_identity.gitea_id.client_id
    ftps_state                                    = "Disabled"
    always_on                                     = true
    minimum_tls_version                           = "1.3"
    vnet_route_all_enabled                        = true

    application_stack {
      docker_registry_url = "https://${data.azurerm_container_registry.mgmt_acr.login_server}"
      docker_image_name   = "microsoft/azuretre/gitea:${local.version}"
    }
  }

  storage_account {
    name         = "gitea-data"
    type         = "AzureFiles"
    account_name = data.azurerm_storage_account.gitea.name
    access_key   = data.azurerm_storage_account.gitea.primary_access_key
    share_name   = azurerm_storage_share.gitea.name
    mount_path   = "/data"
  }

  logs {
    application_logs {
      file_system_level = "Information"
    }

    http_logs {
      file_system {
        retention_in_days = 7
        retention_in_mb   = 100
      }
    }
  }

  depends_on = [
    azurerm_key_vault_secret.gitea_password
  ]
}

resource "azapi_update_resource" "gitea_vnet_container_pull_routing" {
  resource_id = azurerm_linux_web_app.gitea.id
  type        = "Microsoft.Web/sites@2022-09-01"

  body = {
    properties = {
      vnetImagePullEnabled : true
    }
  }

  depends_on = [
    azurerm_linux_web_app.gitea
  ]
}

resource "azapi_resource_action" "restart_gitea_webapp" {
  type        = "Microsoft.Web/sites@2022-09-01"
  resource_id = azurerm_linux_web_app.gitea.id
  method      = "POST"
  action      = "restart"

  depends_on = [
    azapi_update_resource.gitea_vnet_container_pull_routing
  ]
}

resource "azurerm_private_endpoint" "gitea_private_endpoint" {
  name                = "pe-${local.webapp_name}"
  resource_group_name = local.core_resource_group_name
  location            = data.azurerm_resource_group.rg.location
  subnet_id           = data.azurerm_subnet.shared.id
  tags                = local.tre_shared_service_tags

  private_service_connection {
    private_connection_resource_id = azurerm_linux_web_app.gitea.id
    name                           = "psc-${local.webapp_name}"
    subresource_names              = ["sites"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = module.terraform_azurerm_environment_configuration.private_links["privatelink.azurewebsites.net"]
    private_dns_zone_ids = [data.azurerm_private_dns_zone.azurewebsites.id]
  }

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_monitor_diagnostic_setting" "webapp_gitea" {
  name                       = "diag-${var.tre_id}"
  target_resource_id         = azurerm_linux_web_app.gitea.id
  log_analytics_workspace_id = data.azurerm_log_analytics_workspace.tre.id

  dynamic "enabled_log" {
    for_each = [
      for category in data.azurerm_monitor_diagnostic_categories.webapp.log_category_types :
      category if contains(local.webapp_diagnostic_categories_enabled, category)
    ]
    content {
      category = enabled_log.value

    }
  }

  metric {
    category = "AllMetrics"
    enabled  = true
  }
}

resource "azurerm_role_assignment" "keyvault_gitea_role" {
  scope                = data.azurerm_key_vault.keyvault.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.gitea_id.principal_id
}

resource "azurerm_key_vault_secret" "gitea_password" {
  name         = "${local.webapp_name}-administrator-password"
  value        = random_password.gitea_passwd.result
  key_vault_id = data.azurerm_key_vault.keyvault.id
  tags         = local.tre_shared_service_tags

  depends_on = [
    azurerm_role_assignment.keyvault_gitea_role
  ]

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_storage_share" "gitea" {
  name                 = "gitea-data"
  storage_account_name = data.azurerm_storage_account.gitea.name
  quota                = var.gitea_storage_limit
}

resource "azurerm_role_assignment" "gitea_acrpull_role" {
  scope                = data.azurerm_container_registry.mgmt_acr.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.gitea_id.principal_id
}
