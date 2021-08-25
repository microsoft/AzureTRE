resource "azurerm_app_service_plan" "guacamole" {
  name                = "plan-${local.webapp_name}"
  location            = data.azurerm_resource_group.ws.location
  resource_group_name = data.azurerm_resource_group.ws.name
  kind                = "Linux"
  reserved            = "true"

  sku {
    tier = "PremiumV2"
    size = "P1v2"
  }
}

resource "azurerm_app_service" "guacamole" {
  name                = local.webapp_name
  location            = data.azurerm_resource_group.ws.location
  resource_group_name = data.azurerm_resource_group.ws.name
  app_service_plan_id = azurerm_app_service_plan.guacamole.id
  https_only          = true

  site_config {
    linux_fx_version                     = "DOCKER|${data.azurerm_container_registry.mgmt_acr.name}.azurecr.io/${var.image_name}:${var.image_tag}"
    http2_enabled                        = true
    acr_use_managed_identity_credentials = true
  }

  app_settings = {
    WEBSITES_PORT                  = "8080"
    WEBSITE_VNET_ROUTE_ALL         = "1"
    WEBSITE_DNS_SERVER             = "168.63.129.16"
    SCM_DO_BUILD_DURING_DEPLOYMENT = "True"

    TENANT_ID       = data.azurerm_client_config.current.tenant_id
    KEYVAULT_URL    = "${local.kv_url}"

    # Guacmole configuration
    GUAC_DISABLE_COPY     = "${var.guac_disable_copy}"
    GUAC_DISABLE_PASTE    = "${var.guac_disable_paste}"
    GUAC_ENABLE_DRIVE     = "${var.guac_enable_drive}"
    GUAC_DRIVE_NAME       = "${var.guac_drive_name}"
    GUAC_DRIVE_PATH       = "${var.guac_drive_path}"
    GUAC_DISABLE_DOWNLOAD = "${var.guac_disable_download}"
    AUDIENCE              = "${var.api_client_id}"
    ISSUER                = "${local.issuer}"
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
    type = "SystemAssigned"
  }
}

resource "azurerm_role_assignment" "guac_acr_pull" {
  scope                = data.azurerm_container_registry.mgmt_acr.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_app_service.guacamole.identity[0].principal_id
}

resource "azurerm_app_service_virtual_network_swift_connection" "guacamole" {
  app_service_id = azurerm_app_service.guacamole.id
  subnet_id      = data.azurerm_subnet.web_apps.id
}

resource "azurerm_private_endpoint" "guacamole" {
  name                = "pe-${local.webapp_name}"
  location            = data.azurerm_resource_group.ws.location
  resource_group_name = data.azurerm_resource_group.ws.name
  subnet_id           = data.azurerm_subnet.services.id

  private_service_connection {
    private_connection_resource_id = azurerm_app_service.guacamole.id
    name                           = "psc-${local.webapp_name}"
    subresource_names              = ["sites"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "privatelink.azurewebsites.net"
    private_dns_zone_ids = [data.azurerm_private_dns_zone.azurewebsites.id]
  }
}
