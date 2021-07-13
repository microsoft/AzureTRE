# Azure Provider source and version being used
terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "=2.64.0"
    }
  }
}

provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy = var.debug == "true" ? true : false
    }
  }
}

resource "azurerm_resource_group" "core" {
  location = var.location
  name     = "rg-${var.tre_id}"
  tags = {
    project = "Azure Trusted Research Environment"
    tre_id  = var.tre_id
    source  = "https://github.com/microsoft/AzureTRE/"
  }

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_application_insights" "core" {
  name                = "appi-${var.tre_id}"
  resource_group_name = azurerm_resource_group.core.name
  location            = var.location
  application_type    = "web"

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_log_analytics_workspace" "core" {
  name                = "log-${var.tre_id}"
  resource_group_name = azurerm_resource_group.core.name
  location            = var.location
  retention_in_days   = 30
  sku                 = "pergb2018"

  lifecycle { ignore_changes = [tags] }
}

module "network" {
  source              = "./network"
  tre_id              = var.tre_id
  location            = var.location
  resource_group_name = azurerm_resource_group.core.name
  address_space       = var.address_space
}

module "storage" {
  source              = "./storage"
  tre_id              = var.tre_id
  location            = var.location
  resource_group_name = azurerm_resource_group.core.name
  shared_subnet       = module.network.shared
  core_vnet           = module.network.core
}

module "appgateway" {
  source              = "./appgateway"
  tre_id              = var.tre_id
  location            = var.location
  resource_group_name = azurerm_resource_group.core.name
  app_gw_subnet       = module.network.app_gw
  management_api_fqdn = module.api-webapp.management_api_fqdn
  keyvault_id         = module.keyvault.keyvault_id
  depends_on          = [module.keyvault]
}

module "api-webapp" {
  source                                     = "./api-webapp"
  tre_id                                     = var.tre_id
  location                                   = var.location
  resource_group_name                        = azurerm_resource_group.core.name
  web_app_subnet                             = module.network.web_app
  shared_subnet                              = module.network.shared
  app_gw_subnet                              = module.network.app_gw
  core_vnet                                  = module.network.core
  app_insights_connection_string             = azurerm_application_insights.core.connection_string
  app_insights_instrumentation_key           = azurerm_application_insights.core.instrumentation_key
  log_analytics_workspace_id                 = azurerm_log_analytics_workspace.core.id
  management_api_image_repository            = var.management_api_image_repository
  management_api_image_tag                   = var.management_api_image_tag
  docker_registry_server                     = var.docker_registry_server
  docker_registry_username                   = var.docker_registry_username
  docker_registry_password                   = var.docker_registry_password
  state_store_endpoint                       = module.state-store.endpoint
  state_store_key                            = module.state-store.primary_key
  service_bus_resource_request_queue         = module.servicebus.workspacequeue
  service_bus_deployment_status_update_queue = module.servicebus.service_bus_deployment_status_update_queue
  managed_identity                           = module.identity.managed_identity
  azurewebsites_dns_zone_id                  = module.network.azurewebsites_dns_zone_id
  swagger_ui_client_id                       = var.swagger_ui_client_id
  aad_tenant_id                              = var.aad_tenant_id
  api_client_id                              = var.api_client_id
  api_client_secret                          = var.api_client_secret
}

module "identity" {
  source               = "./user-assigned-identity"
  tre_id               = var.tre_id
  location             = var.location
  resource_group_name  = azurerm_resource_group.core.name
  servicebus_namespace = module.servicebus.servicebus_namespace
}

module "resource_processor_function_cnab_driver" {
  count                                      = var.resource_processor_type == "function_cnab_driver" ? 1 : 0
  source                                     = "./processor_function"
  tre_id                                     = var.tre_id
  location                                   = var.location
  resource_group_name                        = azurerm_resource_group.core.name
  app_insights_connection_string             = azurerm_application_insights.core.connection_string
  app_insights_instrumentation_key           = azurerm_application_insights.core.instrumentation_key
  app_service_plan_id                        = module.api-webapp.app_service_plan_id
  storage_account_name                       = module.storage.storage_account_name
  storage_account_access_key                 = module.storage.storage_account_access_key
  storage_state_path                         = module.storage.storage_state_path
  core_vnet                                  = module.network.core
  aci_subnet                                 = module.network.aci
  docker_registry_username                   = var.docker_registry_username
  docker_registry_password                   = var.docker_registry_password
  docker_registry_server                     = var.docker_registry_server
  service_bus_connection_string              = module.servicebus.connection_string
  service_bus_resource_request_queue         = module.servicebus.workspacequeue
  service_bus_deployment_status_update_queue = module.servicebus.service_bus_deployment_status_update_queue
  mgmt_storage_account_name                  = var.mgmt_storage_account_name
  mgmt_resource_group_name                   = var.mgmt_resource_group_name
  terraform_state_container_name             = var.terraform_state_container_name
  porter_output_container_name               = var.porter_output_container_name
  arm_client_id                              = var.resource_processor_client_id
  arm_client_secret                          = var.resource_processor_client_secret
  management_api_image_tag                   = var.management_api_image_tag
  managed_identity                           = module.identity.managed_identity
}

module "resource_processor_vmss_porter" {
  count                                           = var.resource_processor_type == "vmss_porter" ? 1 : 0
  source                                          = "./resource_processor/vmss_porter"
  tre_id                                          = var.tre_id
  location                                        = var.location
  resource_group_name                             = azurerm_resource_group.core.name
  acr_id                                          = data.azurerm_container_registry.mgmt_acr.id
  app_insights_connection_string                  = azurerm_application_insights.core.connection_string
  resource_processor_subnet_id                    = module.network.resource_processor
  docker_registry_server                          = var.docker_registry_server
  resource_processor_vmss_porter_image_repository = var.resource_processor_vmss_porter_image_repository
  resource_processor_vmss_porter_image_tag        = var.resource_processor_vmss_porter_image_tag
  service_bus_connection_string                   = module.servicebus.connection_string
  service_bus_resource_request_queue              = module.servicebus.workspacequeue
  service_bus_deployment_status_update_queue      = module.servicebus.service_bus_deployment_status_update_queue
  mgmt_storage_account_name                       = var.mgmt_storage_account_name
  mgmt_resource_group_name                        = var.mgmt_resource_group_name
  terraform_state_container_name                  = var.terraform_state_container_name
  resource_processor_client_id                    = var.resource_processor_client_id
  resource_processor_client_secret                = var.resource_processor_client_secret
}


module "servicebus" {
  source              = "./servicebus"
  tre_id              = var.tre_id
  location            = var.location
  resource_group_name = azurerm_resource_group.core.name
  shared_subnet       = module.network.shared
  core_vnet           = module.network.core
  tenant_id           = data.azurerm_client_config.current.tenant_id
}

module "keyvault" {
  source                     = "./keyvault"
  tre_id                     = var.tre_id
  location                   = var.location
  resource_group_name        = azurerm_resource_group.core.name
  shared_subnet              = module.network.shared
  core_vnet                  = module.network.core
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  managed_identity_tenant_id = module.identity.managed_identity.tenant_id
  managed_identity_object_id = module.identity.managed_identity.principal_id
  debug                      = var.debug

  depends_on = [
    module.identity
  ]
}

module "firewall" {
  source                     = "./firewall"
  tre_id                     = var.tre_id
  location                   = var.location
  resource_group_name        = azurerm_resource_group.core.name
  log_analytics_workspace_id = azurerm_log_analytics_workspace.core.id

  depends_on = [
    module.network
  ]
}

module "routetable" {
  source                       = "./routetable"
  tre_id                       = var.tre_id
  location                     = var.location
  resource_group_name          = azurerm_resource_group.core.name
  shared_subnet_id             = module.network.shared
  resource_processor_subnet_id = module.network.resource_processor
  firewall_private_ip_address  = module.firewall.firewall_private_ip_address
}

module "acr" {
  source              = "./acr"
  tre_id              = var.tre_id
  location            = var.location
  resource_group_name = azurerm_resource_group.core.name
  core_vnet           = module.network.core
  shared_subnet       = module.network.shared
}

module "state-store" {
  source              = "./state-store"
  tre_id              = var.tre_id
  location            = var.location
  resource_group_name = azurerm_resource_group.core.name
  shared_subnet       = module.network.shared
  core_vnet           = module.network.core
}

module "bastion" {
  source              = "./bastion"
  tre_id              = var.tre_id
  location            = var.location
  resource_group_name = azurerm_resource_group.core.name
  bastion_subnet      = module.network.bastion
}
