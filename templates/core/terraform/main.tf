# Azure Provider source and version being used
terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "=2.71.0"
    }
  }

  backend "azurerm" {}
}

provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy    = var.debug == "true" ? true : false
      recover_soft_deleted_key_vaults = true
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
  shared_subnet       = module.network.shared_subnet_id
  core_vnet           = module.network.core_vnet_id
}

module "appgateway" {
  source                 = "./appgateway"
  tre_id                 = var.tre_id
  location               = var.location
  resource_group_name    = azurerm_resource_group.core.name
  app_gw_subnet          = module.network.app_gw_subnet_id
  shared_subnet          = module.network.shared_subnet_id
  api_fqdn               = module.api-webapp.api_fqdn
  keyvault_id            = module.keyvault.keyvault_id
  static_web_dns_zone_id = module.network.static_web_dns_zone_id
  depends_on             = [module.keyvault]
}

module "api-webapp" {
  source                                     = "./api-webapp"
  tre_id                                     = var.tre_id
  location                                   = var.location
  resource_group_name                        = azurerm_resource_group.core.name
  web_app_subnet                             = module.network.web_app_subnet_id
  shared_subnet                              = module.network.shared_subnet_id
  app_gw_subnet                              = module.network.app_gw_subnet_id
  core_vnet                                  = module.network.core_vnet_id
  app_insights_connection_string             = azurerm_application_insights.core.connection_string
  app_insights_instrumentation_key           = azurerm_application_insights.core.instrumentation_key
  log_analytics_workspace_id                 = azurerm_log_analytics_workspace.core.id
  api_image_repository                       = var.api_image_repository
  api_image_tag                              = var.api_image_tag
  docker_registry_server                     = var.docker_registry_server
  state_store_endpoint                       = module.state-store.endpoint
  cosmosdb_account_name                      = module.state-store.cosmosdb_account_name
  service_bus_resource_request_queue         = module.servicebus.workspacequeue
  service_bus_deployment_status_update_queue = module.servicebus.service_bus_deployment_status_update_queue
  managed_identity                           = module.identity.managed_identity
  azurewebsites_dns_zone_id                  = module.network.azurewebsites_dns_zone_id
  swagger_ui_client_id                       = var.swagger_ui_client_id
  aad_tenant_id                              = var.aad_tenant_id
  api_client_id                              = var.api_client_id
  api_client_secret                          = var.api_client_secret
  acr_id                                     = data.azurerm_container_registry.mgmt_acr.id
  address_space                              = var.address_space
  tre_address_space                          = var.tre_address_space
}

module "identity" {
  source               = "./user-assigned-identity"
  tre_id               = var.tre_id
  location             = var.location
  resource_group_name  = azurerm_resource_group.core.name
  servicebus_namespace = module.servicebus.servicebus_namespace
  cosmos_id            = module.state-store.id
}

module "resource_processor_vmss_porter" {
  count                                           = var.resource_processor_type == "vmss_porter" ? 1 : 0
  source                                          = "./resource_processor/vmss_porter"
  tre_id                                          = var.tre_id
  location                                        = var.location
  resource_group_name                             = azurerm_resource_group.core.name
  acr_id                                          = data.azurerm_container_registry.mgmt_acr.id
  app_insights_connection_string                  = azurerm_application_insights.core.connection_string
  resource_processor_subnet_id                    = module.network.resource_processor_subnet_id
  docker_registry_server                          = var.docker_registry_server
  resource_processor_vmss_porter_image_repository = var.resource_processor_vmss_porter_image_repository
  resource_processor_vmss_porter_image_tag        = var.resource_processor_vmss_porter_image_tag
  service_bus_namespace_id                        = module.servicebus.id
  service_bus_resource_request_queue              = module.servicebus.workspacequeue
  service_bus_deployment_status_update_queue      = module.servicebus.service_bus_deployment_status_update_queue
  mgmt_storage_account_name                       = var.mgmt_storage_account_name
  mgmt_resource_group_name                        = var.mgmt_resource_group_name
  terraform_state_container_name                  = var.terraform_state_container_name
  keyvault_id                                     = module.keyvault.keyvault_id

  depends_on = [
    module.keyvault,
    module.firewall
  ]
}

module "servicebus" {
  source                       = "./servicebus"
  tre_id                       = var.tre_id
  location                     = var.location
  resource_group_name          = azurerm_resource_group.core.name
  core_vnet                    = module.network.core_vnet_id
  resource_processor_subnet_id = module.network.resource_processor_subnet_id
}

module "keyvault" {
  source                     = "./keyvault"
  tre_id                     = var.tre_id
  location                   = var.location
  resource_group_name        = azurerm_resource_group.core.name
  shared_subnet              = module.network.shared_subnet_id
  core_vnet                  = module.network.core_vnet_id
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
  deploy_gitea               = var.deploy_gitea
  deploy_nexus               = var.deploy_nexus

  depends_on = [
    module.network
  ]
}

module "routetable" {
  source                       = "./routetable"
  tre_id                       = var.tre_id
  location                     = var.location
  resource_group_name          = azurerm_resource_group.core.name
  shared_subnet_id             = module.network.shared_subnet_id
  resource_processor_subnet_id = module.network.resource_processor_subnet_id
  web_app_subnet_id            = module.network.web_app_subnet_id
  app_gw_subnet_id             = module.network.app_gw_subnet_id
  firewall_private_ip_address  = module.firewall.firewall_private_ip_address
}

module "state-store" {
  source              = "./state-store"
  tre_id              = var.tre_id
  location            = var.location
  resource_group_name = azurerm_resource_group.core.name
  shared_subnet       = module.network.shared_subnet_id
  core_vnet           = module.network.core_vnet_id
}

module "bastion" {
  source              = "./bastion"
  tre_id              = var.tre_id
  location            = var.location
  resource_group_name = azurerm_resource_group.core.name
  bastion_subnet      = module.network.bastion_subnet_id
}

module "gitea" {
  count                  = var.deploy_gitea == true ? 1 : 0
  source                 = "../../shared_services/gitea/terraform"
  tre_id                 = var.tre_id
  location               = var.location
  image_tag              = var.gitea_image_tag
  docker_registry_server = data.azurerm_container_registry.mgmt_acr.login_server
  acr_id                 = data.azurerm_container_registry.mgmt_acr.id
  keyvault_id            = module.keyvault.keyvault_id
  storage_account_name   = module.storage.storage_account_name

  depends_on = [
    module.network,
    module.api-webapp # it would have been better to depend on the plan itself and not the whole module
  ]
}

module "nexus" {
  count                = var.deploy_nexus == true ? 1 : 0
  source               = "../../shared_services/sonatype-nexus/terraform"
  tre_id               = var.tre_id
  location             = var.location
  storage_account_name = module.storage.storage_account_name

  depends_on = [
    module.network,
    module.api-webapp # it would have been better to depend on the plan itself and not the whole module
  ]
}
