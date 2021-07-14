resource "azurerm_app_service_plan" "inference" {
  name                = "asp-inf-${local.service_resource_name_suffix}"
  location            = data.azurerm_resource_group.ws.location
  resource_group_name = data.azurerm_resource_group.ws.name
  kind                = "Linux"
  reserved            = "true"

  sku {
    tier = "PremiumV2"
    size = "P1v2"
  }
}

resource "azurerm_app_service" "inference" {
  name                = "app-inf-${local.service_resource_name_suffix}"
  location            = data.azurerm_resource_group.ws.location
  resource_group_name = data.azurerm_resource_group.ws.name
  app_service_plan_id = azurerm_app_service_plan.inference.id
  https_only          = true

  site_config {
    always_on     = true
    http2_enabled = true
  }

  app_settings = {
    "WEBSITE_VNET_ROUTE_ALL"         = "1"
    "WEBSITE_DNS_SERVER"             = "168.63.129.16"
    "SCM_DO_BUILD_DURING_DEPLOYMENT" = "True"

    "APPLICATION_ID"    = var.inference_sp_client_id
    "CLUSTER"           = var.azureml_compute_cluster_name
    "WORKSPACE_NAME"    = var.azureml_workspace_name
    "EXPERIMENT_NAME"   = "main"
    "RESOURCE_GROUP"    = data.azurerm_resource_group.ws.name
    "SUBSCRIPTION_ID"   = data.azurerm_client_config.current.subscription_id
    "TENANT_ID"         = data.azurerm_client_config.current.tenant_id
    "DATASTORE_NAME"    = "inferencedatastore"
    "IMAGE_DATA_FOLDER" = "imagedata"
  }

  connection_string {
    name  = "AZUREML_SERVICE_PRINCIPAL_SECRET"
    type  = "Custom"
    value = var.inference_sp_client_secret
  }

  connection_string {
    name  = "API_AUTH_SECRET"
    type  = "Custom"
    value = random_uuid.inference_auth_key.result
  }

}

resource "azurerm_app_service_virtual_network_swift_connection" "inference" {
  app_service_id = azurerm_app_service.inference.id
  subnet_id      = data.azurerm_subnet.web_apps.id
}

resource "azurerm_private_endpoint" "inference" {
  name                = "pe-inference-${var.tre_id}"
  location            = data.azurerm_resource_group.ws.location
  resource_group_name = data.azurerm_resource_group.ws.name
  subnet_id           = data.azurerm_subnet.services.id

  private_service_connection {
    private_connection_resource_id = azurerm_app_service.inference.id
    name                           = "psc-inference-${var.tre_id}"
    subresource_names              = ["sites"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "privatelink.azurewebsites.net"
    private_dns_zone_ids = [data.azurerm_private_dns_zone.azurewebsites.id]
  }
}
