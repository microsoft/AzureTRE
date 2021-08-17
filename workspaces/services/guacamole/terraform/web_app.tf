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
    linux_fx_version                     = "DOCKER|${data.azurerm_container_registry.mgmt_acr.name}.azurecr.io/guac-server:v0.1.0"
    http2_enabled                        = true
    acr_use_managed_identity_credentials = true
  }

  app_settings = {
    "WEBSITE_VNET_ROUTE_ALL"         = "1"
    "WEBSITE_DNS_SERVER"             = "168.63.129.16"
    "SCM_DO_BUILD_DURING_DEPLOYMENT" = "True"

    "RESOURCE_GROUP"  = data.azurerm_resource_group.ws.name
    "SUBSCRIPTION_ID" = data.azurerm_client_config.current.subscription_id
    "TENANT_ID"       = data.azurerm_client_config.current.tenant_id

    WEBSITES_PORT = "8080"
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
