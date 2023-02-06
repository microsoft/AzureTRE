resource "local_file" "mlflow_windows_config" {
  content  = data.template_file.mlflow_windows_config.rendered
  filename = "${path.module}/../mlflow-vm-config/windows/config.ps1"
}

resource "local_file" "mlflow_linux_config" {
  content  = data.template_file.mlflow_linux_config.rendered
  filename = "${path.module}/../mlflow-vm-config/linux/config.sh"
}

resource "azurerm_storage_share_file" "mlflow_config_windows" {
  name             = "mlflow-windows-config-${local.webapp_name}.ps1"
  storage_share_id = data.azurerm_storage_share.shared_storage.id
  source           = "${path.module}/../mlflow-vm-config/windows/config.ps1"
}

resource "azurerm_storage_share_file" "mlflow_config_linux" {
  name             = "mlflow-linux-config-${local.webapp_name}.sh"
  storage_share_id = data.azurerm_storage_share.shared_storage.id
  source           = "${path.module}/../mlflow-vm-config/linux/config.sh"
}

resource "azurerm_storage_container" "mlflow_artefacts" {
  name                  = local.mlflow_artefacts_container_name
  storage_account_name  = local.storage_name
  container_access_type = "private"
}

resource "azurerm_linux_web_app" "mlflow" {
  name                            = local.webapp_name
  location                        = data.azurerm_resource_group.ws.location
  resource_group_name             = data.azurerm_resource_group.ws.name
  service_plan_id                 = data.azurerm_service_plan.workspace.id
  https_only                      = true
  key_vault_reference_identity_id = azurerm_user_assigned_identity.mlflow.id
  virtual_network_subnet_id       = data.azurerm_subnet.web_apps.id
  tags                            = local.tre_workspace_service_tags

  site_config {
    http2_enabled                                 = true
    container_registry_use_managed_identity       = true
    container_registry_managed_identity_client_id = azurerm_user_assigned_identity.mlflow.client_id
    ftps_state                                    = "Disabled"
    vnet_route_all_enabled                        = true
    minimum_tls_version                           = "1.2"

    application_stack {
      docker_image     = "${data.azurerm_container_registry.mgmt_acr.login_server}/microsoft/azuretre/${local.image_name}"
      docker_image_tag = local.image_tag
    }
  }

  app_settings = {
    MLFLOW_SERVER_WORKERS = "1"
    MLFLOW_SERVER_PORT    = "5000"
    MLFLOW_SERVER_HOST    = "0.0.0.0"

    MLFLOW_SERVER_FILE_STORE            = format("%s%s%s%s%s%s%s%s%s%s", "postgresql://", random_string.username.result, "@", azurerm_postgresql_server.mlflow.name, ":", random_password.password.result, "@", azurerm_postgresql_server.mlflow.name, ".postgres.database.azure.com:5432/", azurerm_postgresql_database.mlflow.name)
    MLFLOW_SERVER_DEFAULT_ARTIFACT_ROOT = format("%s%s%s%s%s%s", "wasbs://", azurerm_storage_container.mlflow_artefacts.name, "@", data.azurerm_storage_account.mlflow.name, ".blob.core.windows.net/", azurerm_storage_container.mlflow_artefacts.name)
    AZURE_STORAGE_CONNECTION_STRING     = data.azurerm_storage_account.mlflow.primary_connection_string
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
    identity_ids = [azurerm_user_assigned_identity.mlflow.id]
  }

  lifecycle { ignore_changes = [tags] }

  depends_on = [
    azurerm_role_assignment.mlflow_acr_pull,
    azurerm_key_vault_access_policy.mlflow,
  ]
}

resource "azurerm_monitor_diagnostic_setting" "mlflow" {
  name                       = "diag-${var.tre_id}"
  target_resource_id         = azurerm_linux_web_app.mlflow.id
  log_analytics_workspace_id = data.azurerm_log_analytics_workspace.tre.id

  dynamic "log" {
    for_each = data.azurerm_monitor_diagnostic_categories.mlflow.log_category_types
    content {
      category = log.value
      enabled  = contains(local.web_app_diagnostic_categories_enabled, log.value) ? true : false

      retention_policy {
        enabled = contains(local.web_app_diagnostic_categories_enabled, log.value) ? true : false
        days    = 365
      }
    }
  }
}

resource "azurerm_role_assignment" "mlflow_acr_pull" {
  scope                = data.azurerm_container_registry.mgmt_acr.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.mlflow.principal_id
}

resource "azurerm_private_endpoint" "mlflow" {
  # disabling this makes the webapp available on the public internet
  count = var.is_exposed_externally == false ? 1 : 0

  name                = "pe-${local.webapp_name}"
  location            = data.azurerm_resource_group.ws.location
  resource_group_name = data.azurerm_resource_group.ws.name
  subnet_id           = data.azurerm_subnet.services.id
  tags                = local.tre_workspace_service_tags

  private_service_connection {
    private_connection_resource_id = azurerm_linux_web_app.mlflow.id
    name                           = "psc-${local.webapp_name}"
    subresource_names              = ["sites"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "privatelink.azurewebsites.net"
    private_dns_zone_ids = [data.azurerm_private_dns_zone.azurewebsites.id]
  }
}

resource "azurerm_key_vault_access_policy" "mlflow" {
  key_vault_id = data.azurerm_key_vault.ws.id
  tenant_id    = azurerm_user_assigned_identity.mlflow.tenant_id
  object_id    = azurerm_user_assigned_identity.mlflow.principal_id

  secret_permissions = ["Get", "List", ]
}

resource "azurerm_user_assigned_identity" "mlflow" {
  resource_group_name = data.azurerm_resource_group.ws.name
  location            = data.azurerm_resource_group.ws.location
  name                = local.identity_name
  tags                = local.tre_workspace_service_tags

  lifecycle { ignore_changes = [tags] }
}
