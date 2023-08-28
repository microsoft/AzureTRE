resource "random_password" "gitea_passwd" {
  length      = 20
  min_upper   = 2
  min_lower   = 2
  min_numeric = 2
  min_special = 2
}

# we have to use user-assigned to break a cycle in the dependencies: app identity, kv-policy, secrets in app settings
resource "azurerm_user_assigned_identity" "gitea_id" {
  resource_group_name = data.azurerm_resource_group.ws.name
  location            = data.azurerm_resource_group.ws.location
  tags                = local.workspace_service_tags

  name = "id-gitea-${local.service_resource_name_suffix}"

  lifecycle { ignore_changes = [tags] }
}

data "azurerm_service_plan" "workspace" {
  name                = "plan-${var.workspace_id}"
  resource_group_name = data.azurerm_resource_group.ws.name
}

resource "azurerm_linux_web_app" "gitea" {
  name                            = local.webapp_name
  location                        = data.azurerm_resource_group.ws.location
  resource_group_name             = data.azurerm_resource_group.ws.name
  service_plan_id                 = data.azurerm_service_plan.workspace.id
  https_only                      = true
  key_vault_reference_identity_id = azurerm_user_assigned_identity.gitea_id.id
  virtual_network_subnet_id       = data.azurerm_subnet.web_apps.id
  tags                            = local.workspace_service_tags

  app_settings = {
    WEBSITES_PORT                                    = "3000"
    WEBSITES_ENABLE_APP_SERVICE_STORAGE              = true
    GITEA_USERNAME                                   = "giteaadmin"
    GITEA_PASSWD                                     = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.gitea_password.id})"
    GITEA_EMAIL                                      = "giteaadmin@azuretre.com"
    GITEA_OPENID_CLIENT_ID                           = data.azurerm_key_vault_secret.client_id.value
    GITEA_OPENID_CLIENT_SECRET                       = data.azurerm_key_vault_secret.client_secret.value
    GITEA_OPENID_AUTHORITY                           = "https://login.microsoftonline.com/${data.azurerm_key_vault_secret.aad_tenant_id.value}/v2.0"
    GITEA__server__ROOT_URL                          = "https://${local.webapp_name}.azurewebsites.net/"
    GITEA__server__LFS_START_SERVER                  = "true"
    GITEA__server__OFFLINE_MODE                      = true
    GITEA__lfs__PATH                                 = "/data/gitea/lfs"
    GITEA__lfs__STORAGE_TYPE                         = "local"
    GITEA__log_0x2E_console__COLORIZE                = "false" # Azure monitor doens't show colors, so this is easier to read.
    GITEA__openid__ENABLE_OPENID_SIGNIN              = "true"
    GITEA__openid__ENABLE_OPENID_SIGNUP              = "false"
    GITEA__picture__DISABLE_GRAVATAR                 = "true" # external avaters are not available due to network restrictions
    GITEA__security__INSTALL_LOCK                    = true
    GITEA__service__DISABLE_REGISTRATION             = false
    GITEA__service__ALLOW_ONLY_EXTERNAL_REGISTRATION = true
    GITEA__service__SHOW_REGISTRATION_BUTTON         = false
    GITEA__database__SSL_MODE                        = "true"
    GITEA__database__DB_TYPE                         = "mysql"
    GITEA__database__HOST                            = azurerm_mysql_flexible_server.gitea.fqdn
    GITEA__database__NAME                            = azurerm_mysql_flexible_database.gitea.name
    GITEA__database__USER                            = "${azurerm_mysql_flexible_server.gitea.administrator_login}"
    GITEA__database__PASSWD                          = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.db_password.id})"
    GITEA__ALLOWED_DOMAIN                            = "gitea-${var.tre_id}.azurewebsites.net"
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
    minimum_tls_version                           = "1.2"
    vnet_route_all_enabled                        = true

    application_stack {
      docker_image     = "${data.azurerm_container_registry.mgmt_acr.login_server}/microsoft/azuretre/gitea-workspace-service"
      docker_image_tag = local.version
    }
  }

  storage_account {
    name         = "gitea-data"
    type         = "AzureFiles"
    account_name = azurerm_storage_account.gitea.name
    access_key   = azurerm_storage_account.gitea.primary_access_key
    share_name   = azurerm_storage_share.gitea.name
    mount_path   = "/data/gitea/"
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

resource "azurerm_private_endpoint" "gitea_private_endpoint" {
  name                = "pe-${local.webapp_name}"
  location            = data.azurerm_resource_group.ws.location
  resource_group_name = data.azurerm_resource_group.ws.name
  subnet_id           = data.azurerm_subnet.services.id
  tags                = local.workspace_service_tags

  private_service_connection {
    private_connection_resource_id = azurerm_linux_web_app.gitea.id
    name                           = "psc-${local.webapp_name}"
    subresource_names              = ["sites"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "privatelink.azurewebsites.net"
    private_dns_zone_ids = [data.azurerm_private_dns_zone.azurewebsites.id]
  }

  lifecycle { ignore_changes = [tags] }
}
resource "azurerm_monitor_diagnostic_setting" "gitea" {
  name                       = "diag-${local.service_resource_name_suffix}"
  target_resource_id         = azurerm_linux_web_app.gitea.id
  log_analytics_workspace_id = data.azurerm_log_analytics_workspace.tre.id

  dynamic "log" {
    for_each = data.azurerm_monitor_diagnostic_categories.gitea.log_category_types
    content {
      category = log.value
      enabled  = contains(local.web_app_diagnostic_categories_enabled, log.value) ? true : false
    }
  }

  metric {
    category = "AllMetrics"
    enabled  = true
  }
}

resource "azurerm_key_vault_access_policy" "gitea_policy" {
  key_vault_id = data.azurerm_key_vault.ws.id
  tenant_id    = azurerm_user_assigned_identity.gitea_id.tenant_id
  object_id    = azurerm_user_assigned_identity.gitea_id.principal_id

  secret_permissions = ["Get", "List", ]
}

resource "azurerm_key_vault_secret" "gitea_password" {
  name         = "${local.webapp_name}-administrator-password"
  value        = random_password.gitea_passwd.result
  key_vault_id = data.azurerm_key_vault.ws.id
  tags         = local.workspace_service_tags

  depends_on = [
    azurerm_key_vault_access_policy.gitea_policy
  ]
}

resource "azurerm_role_assignment" "gitea_acrpull_role" {
  scope                = data.azurerm_container_registry.mgmt_acr.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.gitea_id.principal_id
}
