# we have to use user-assigned to break a cycle in the dependencies: app identity, kv-policy, secrets in app settings
resource "azurerm_user_assigned_identity" "guacamole_id" {
  resource_group_name = data.azurerm_resource_group.ws.name
  location            = data.azurerm_resource_group.ws.location
  name                = local.identity_name
  tags                = local.workspace_service_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_linux_web_app" "guacamole" {
  name                                           = local.webapp_name
  location                                       = data.azurerm_resource_group.ws.location
  resource_group_name                            = data.azurerm_resource_group.ws.name
  service_plan_id                                = data.azurerm_service_plan.workspace.id
  https_only                                     = true
  key_vault_reference_identity_id                = azurerm_user_assigned_identity.guacamole_id.id
  virtual_network_subnet_id                      = data.azurerm_subnet.web_apps.id
  ftp_publish_basic_authentication_enabled       = false
  webdeploy_publish_basic_authentication_enabled = false
  tags                                           = local.workspace_service_tags
  public_network_access_enabled                  = var.is_exposed_externally

  site_config {
    http2_enabled                                 = true
    container_registry_use_managed_identity       = true
    container_registry_managed_identity_client_id = azurerm_user_assigned_identity.guacamole_id.client_id
    ftps_state                                    = "Disabled"
    vnet_route_all_enabled                        = true
    minimum_tls_version                           = "1.3"

    application_stack {
      docker_registry_url = "https://${data.azurerm_container_registry.mgmt_acr.login_server}"
      docker_image_name   = "microsoft/azuretre/${var.image_name}:${local.image_tag}"
    }
  }

  app_settings = {
    WEBSITES_PORT              = "8085"
    TENANT_ID                  = data.azurerm_client_config.current.tenant_id
    KEYVAULT_URL               = data.azurerm_key_vault.ws.vault_uri
    API_URL                    = local.api_url
    SERVICE_ID                 = var.tre_resource_id
    WORKSPACE_ID               = var.workspace_id
    MANAGED_IDENTITY_CLIENT_ID = azurerm_user_assigned_identity.guacamole_id.client_id

    APPLICATIONINSIGHTS_CONNECTION_STRING             = data.azurerm_application_insights.ws.connection_string
    APPLICATIONINSIGHTS_INSTRUMENTATION_LOGGING_LEVEL = "INFO"

    # Guacmole configuration
    GUAC_DISABLE_COPY     = var.guac_disable_copy
    GUAC_DISABLE_PASTE    = var.guac_disable_paste
    GUAC_ENABLE_DRIVE     = var.guac_enable_drive
    GUAC_DRIVE_NAME       = var.guac_drive_name
    GUAC_DRIVE_PATH       = var.guac_drive_path
    GUAC_DISABLE_DOWNLOAD = var.guac_disable_download
    GUAC_DISABLE_UPLOAD   = var.guac_disable_upload
    GUAC_SERVER_LAYOUT    = var.guac_server_layout

    AUDIENCE = "@Microsoft.KeyVault(SecretUri=${data.azurerm_key_vault_secret.workspace_client_id.id})"
    ISSUER   = local.issuer

    OAUTH2_PROXY_CLIENT_ID       = "@Microsoft.KeyVault(SecretUri=${data.azurerm_key_vault_secret.workspace_client_id.id})"
    OAUTH2_PROXY_CLIENT_SECRET   = "@Microsoft.KeyVault(SecretUri=${data.azurerm_key_vault_secret.workspace_client_secret.id})"
    OAUTH2_PROXY_REDIRECT_URI    = "https://${local.webapp_name}.${local.webapp_suffix}/oauth2/callback"
    OAUTH2_PROXY_EMAIL_DOMAIN    = "\"*\"" # oauth proxy will allow all email domains only when the value is "*"
    OAUTH2_PROXY_OIDC_ISSUER_URL = local.issuer
    OAUTH2_PROXY_JWKS_ENDPOINT   = local.jwks_endpoint
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

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.guacamole_id.id]
  }

  lifecycle { ignore_changes = [tags] }

  depends_on = [
    azurerm_role_assignment.guac_acr_pull,
    azurerm_role_assignment.keyvault_guacamole_ws_role
  ]
}

resource "azapi_update_resource" "guac_vnet_container_pull_routing" {
  resource_id = azurerm_linux_web_app.guacamole.id
  type        = "Microsoft.Web/sites@2022-09-01"

  body = {
    properties = {
      vnetImagePullEnabled : true
    }
  }

  depends_on = [
    azurerm_linux_web_app.guacamole
  ]
}

resource "azapi_resource_action" "restart_guac_webapp" {
  type        = "Microsoft.Web/sites@2022-09-01"
  resource_id = azurerm_linux_web_app.guacamole.id
  method      = "POST"
  action      = "restart"

  depends_on = [
    azapi_update_resource.guac_vnet_container_pull_routing
  ]
}

resource "azurerm_monitor_diagnostic_setting" "guacamole" {
  name                       = "diag-${var.tre_id}"
  target_resource_id         = azurerm_linux_web_app.guacamole.id
  log_analytics_workspace_id = data.azurerm_log_analytics_workspace.tre.id

  dynamic "enabled_log" {
    for_each = setintersection(data.azurerm_monitor_diagnostic_categories.guacamole.log_category_types, local.guacamole_diagnostic_categories_enabled)
    content {
      category = enabled_log.value
    }
  }

  metric {
    category = "AllMetrics"
    enabled  = true
  }
}

resource "azurerm_role_assignment" "guac_acr_pull" {
  scope                = data.azurerm_container_registry.mgmt_acr.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.guacamole_id.principal_id
}

resource "azurerm_private_endpoint" "guacamole" {
  # disabling this makes the webapp available on the public internet
  count               = var.is_exposed_externally == false ? 1 : 0
  name                = "pe-${local.webapp_name}"
  location            = data.azurerm_resource_group.ws.location
  resource_group_name = data.azurerm_resource_group.ws.name
  subnet_id           = data.azurerm_subnet.services.id
  tags                = local.workspace_service_tags

  private_service_connection {
    private_connection_resource_id = azurerm_linux_web_app.guacamole.id
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

resource "azurerm_role_assignment" "keyvault_guacamole_ws_role" {
  scope                = data.azurerm_key_vault.ws.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.guacamole_id.principal_id
}
