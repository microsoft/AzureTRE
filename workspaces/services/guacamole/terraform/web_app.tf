resource "azurerm_app_service_plan" "guacamole" {
  name                = "plan-inf-${local.service_resource_name_suffix}"
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
  name                = "guacamole-${local.service_resource_name_suffix}"
  location            = data.azurerm_resource_group.ws.location
  resource_group_name = data.azurerm_resource_group.ws.name
  app_service_plan_id = azurerm_app_service_plan.guacamole.id
  https_only          = true

  site_config {
    linux_fx_version = "DOCKER|${var.acr_name}.azurecr.io/guac-server:${var.guacamole_image_tag}"
    always_on        = true
    http2_enabled    = true
  }

  app_settings = {
    "WEBSITE_VNET_ROUTE_ALL"         = "1"
    "WEBSITE_DNS_SERVER"             = "168.63.129.16"
    "SCM_DO_BUILD_DURING_DEPLOYMENT" = "True"

    "RESOURCE_GROUP"    = data.azurerm_resource_group.ws.name
    "SUBSCRIPTION_ID"   = data.azurerm_client_config.current.subscription_id
    "TENANT_ID"         = data.azurerm_client_config.current.tenant_id

    WEBSITES_PORT       = "8080"
  }
  
  identity {
    type = "SystemAssigned"
  }
}

# The WebApp uses managed identity to login to ACR
# https://github.com/Azure/app-service-linux-docs/blob/master/HowTo/use_system-assigned_managed_identities.md
# Depends if this tf script if being executed with a SP or a managed identity we have to options to do az login
# az login using SP (local runs)
resource "null_resource" "az_sp_update_acr_permissions" {

  count = var.arm_client_id != "" ? 1 : 0
  provisioner "local-exec" {
    command = "az login --service-principal --username ${var.arm_client_id} --password ${var.arm_client_secret} --tenant ${var.arm_tenant_id} && az resource update --ids ${azurerm_app_service.guacamole.id}/config/web --set properties.acrUseManagedIdentityCreds=True -o none"
  }
}

# Managed az login (for CI)
resource "null_resource" "az_managed_update_acr_permissions" {

  count = data.azurerm_client_config.current.client_id != "" && var.arm_client_id == "" ? 1 : 0
  provisioner "local-exec" {
    command = "az login --identity -u '${data.azurerm_client_config.current.client_id}' && az resource update --ids ${azurerm_app_service.guacamole.id}/config/web --set properties.acrUseManagedIdentityCreds=True -o none"
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
  name                = "pe-guacamole-${var.tre_id}"
  location            = data.azurerm_resource_group.ws.location
  resource_group_name = data.azurerm_resource_group.ws.name
  subnet_id           = data.azurerm_subnet.services.id

  private_service_connection {
    private_connection_resource_id = azurerm_app_service.guacamole.id
    name                           = "psc-guacamole-${var.tre_id}"
    subresource_names              = ["sites"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "privatelink.azurewebsites.net"
    private_dns_zone_ids = [data.azurerm_private_dns_zone.azurewebsites.id]
  }
}
