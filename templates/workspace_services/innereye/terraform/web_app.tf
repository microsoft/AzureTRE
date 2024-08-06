data "azurerm_app_service_plan" "workspace" {
  name                = "plan-${var.workspace_id}"
  resource_group_name = data.azurerm_resource_group.ws.name
}


resource "random_uuid" "inference_auth_key" {
}

resource "azurerm_app_service" "inference" {
  name                = "app-inf-${local.service_resource_name_suffix}"
  location            = data.azurerm_resource_group.ws.location
  resource_group_name = data.azurerm_resource_group.ws.name
  app_service_plan_id = data.azurerm_app_service_plan.workspace.id
  https_only          = true
  tags                = local.tre_workspace_service_tags

  site_config {
    always_on     = true
    http2_enabled = true
  }

  app_settings = {
    "WEBSITE_VNET_ROUTE_ALL"         = "1"
    "WEBSITE_DNS_SERVER"             = "168.63.129.16"
    "SCM_DO_BUILD_DURING_DEPLOYMENT" = "True"

    "APPLICATION_ID"    = var.inference_sp_client_id
    "CLUSTER"           = local.aml_compute_cluster_name
    "WORKSPACE_NAME"    = local.aml_workspace_name
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

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_app_service_virtual_network_swift_connection" "inference" {
  app_service_id = azurerm_app_service.inference.id
  subnet_id      = data.azurerm_subnet.web_apps.id
}

data "azurerm_private_dns_zone" "azurewebsites" {
  name                = module.terraform_azurerm_environment_configuration.private_links["privatelink.azurewebsites.net"]
  resource_group_name = local.core_resource_group_name
}

resource "azurerm_private_endpoint" "inference" {
  name                = "pe-inference-${local.service_resource_name_suffix}"
  location            = data.azurerm_resource_group.ws.location
  resource_group_name = data.azurerm_resource_group.ws.name
  subnet_id           = data.azurerm_subnet.services.id
  tags                = local.tre_workspace_service_tags

  private_service_connection {
    private_connection_resource_id = azurerm_app_service.inference.id
    name                           = "psc-inference-${local.service_resource_name_suffix}"
    subresource_names              = ["sites"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = module.terraform_azurerm_environment_configuration.private_links["privatelink.azurewebsites.net"]
    private_dns_zone_ids = [data.azurerm_private_dns_zone.azurewebsites.id]
  }

  lifecycle { ignore_changes = [tags] }
}
