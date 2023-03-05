# Azure Provider source and version being used
terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "=3.41.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.4.0"
    }
    local = {
      source  = "hashicorp/local"
      version = "~> 2.3.0"
    }
    http = {
      source  = "hashicorp/http"
      version = "~> 3.2.0"
    }
  }

  backend "azurerm" {}
}

provider "azurerm" {
  features {
    key_vault {
      # Don't purge on destroy (this would fail due to purge protection being enabled on keyvault)
      purge_soft_delete_on_destroy               = false
      purge_soft_deleted_secrets_on_destroy      = false
      purge_soft_deleted_certificates_on_destroy = false
      purge_soft_deleted_keys_on_destroy         = false
      # When recreating an environment, recover any previously soft deleted secrets - set to true by default
      recover_soft_deleted_key_vaults   = true
      recover_soft_deleted_secrets      = true
      recover_soft_deleted_certificates = true
      recover_soft_deleted_keys         = true
    }
  }
}

resource "azurerm_resource_group" "core" {
  location = var.location
  name     = "rg-${var.tre_id}"
  tags = {
    project    = "Azure Trusted Research Environment"
    tre_id     = var.tre_id
    source     = "https://github.com/microsoft/AzureTRE/"
    ci_git_ref = var.ci_git_ref # TODO: not include if empty
  }

  lifecycle { ignore_changes = [tags] }
}

module "azure_monitor" {
  source                                   = "./azure-monitor"
  tre_id                                   = var.tre_id
  location                                 = var.location
  resource_group_name                      = azurerm_resource_group.core.name
  shared_subnet_id                         = module.network.shared_subnet_id
  azure_monitor_dns_zone_id                = module.network.azure_monitor_dns_zone_id
  azure_monitor_oms_opinsights_dns_zone_id = module.network.azure_monitor_oms_opinsights_dns_zone_id
  azure_monitor_ods_opinsights_dns_zone_id = module.network.azure_monitor_ods_opinsights_dns_zone_id
  azure_monitor_agentsvc_dns_zone_id       = module.network.azure_monitor_agentsvc_dns_zone_id
  blob_core_dns_zone_id                    = module.network.blob_core_dns_zone_id
  tre_core_tags                            = local.tre_core_tags
  enable_local_debugging                   = var.enable_local_debugging

  depends_on = [
    module.network
  ]
}

module "network" {
  source              = "./network"
  tre_id              = var.tre_id
  location            = var.location
  resource_group_name = azurerm_resource_group.core.name
  core_address_space  = var.core_address_space
}

module "appgateway" {
  source                     = "./appgateway"
  tre_id                     = var.tre_id
  location                   = var.location
  resource_group_name        = azurerm_resource_group.core.name
  app_gw_subnet              = module.network.app_gw_subnet_id
  shared_subnet              = module.network.shared_subnet_id
  api_fqdn                   = azurerm_linux_web_app.api.default_hostname
  keyvault_id                = azurerm_key_vault.kv.id
  static_web_dns_zone_id     = module.network.static_web_dns_zone_id
  log_analytics_workspace_id = module.azure_monitor.log_analytics_workspace_id

  depends_on = [
    module.network,
    azurerm_key_vault.kv,
    azurerm_key_vault_access_policy.deployer,
    azurerm_private_endpoint.api_private_endpoint
  ]
}

module "airlock_resources" {
  source                                = "./airlock"
  tre_id                                = var.tre_id
  location                              = var.location
  resource_group_name                   = azurerm_resource_group.core.name
  airlock_storage_subnet_id             = module.network.airlock_storage_subnet_id
  airlock_events_subnet_id              = module.network.airlock_events_subnet_id
  docker_registry_server                = local.docker_registry_server
  mgmt_resource_group_name              = var.mgmt_resource_group_name
  mgmt_acr_name                         = var.acr_name
  api_principal_id                      = azurerm_user_assigned_identity.id.principal_id
  airlock_app_service_plan_sku          = var.core_app_service_plan_sku
  airlock_processor_subnet_id           = module.network.airlock_processor_subnet_id
  airlock_servicebus                    = azurerm_servicebus_namespace.sb
  applicationinsights_connection_string = module.azure_monitor.app_insights_connection_string
  enable_malware_scanning               = var.enable_airlock_malware_scanning
  tre_core_tags                         = local.tre_core_tags
  log_analytics_workspace_id            = module.azure_monitor.log_analytics_workspace_id
  blob_core_dns_zone_id                 = module.network.blob_core_dns_zone_id
  file_core_dns_zone_id                 = module.network.file_core_dns_zone_id
  queue_core_dns_zone_id                = module.network.queue_core_dns_zone_id
  table_core_dns_zone_id                = module.network.table_core_dns_zone_id

  enable_local_debugging = var.enable_local_debugging
  myip                   = local.myip

  depends_on = [
    azurerm_servicebus_namespace.sb,
    module.network
  ]
}

module "resource_processor_vmss_porter" {
  count                                            = var.resource_processor_type == "vmss_porter" ? 1 : 0
  source                                           = "./resource_processor/vmss_porter"
  tre_id                                           = var.tre_id
  location                                         = var.location
  resource_group_name                              = azurerm_resource_group.core.name
  acr_id                                           = data.azurerm_container_registry.mgmt_acr.id
  app_insights_connection_string                   = module.azure_monitor.app_insights_connection_string
  resource_processor_subnet_id                     = module.network.resource_processor_subnet_id
  docker_registry_server                           = local.docker_registry_server
  resource_processor_vmss_porter_image_repository  = var.resource_processor_vmss_porter_image_repository
  service_bus_namespace_id                         = azurerm_servicebus_namespace.sb.id
  service_bus_resource_request_queue               = azurerm_servicebus_queue.workspacequeue.name
  service_bus_deployment_status_update_queue       = azurerm_servicebus_queue.service_bus_deployment_status_update_queue.name
  mgmt_storage_account_name                        = var.mgmt_storage_account_name
  mgmt_resource_group_name                         = var.mgmt_resource_group_name
  terraform_state_container_name                   = var.terraform_state_container_name
  key_vault_name                                   = azurerm_key_vault.kv.name
  key_vault_url                                    = azurerm_key_vault.kv.vault_uri
  key_vault_id                                     = azurerm_key_vault.kv.id
  subscription_id                                  = var.arm_subscription_id
  resource_processor_number_processes_per_instance = var.resource_processor_number_processes_per_instance
  resource_processor_vmss_sku                      = var.resource_processor_vmss_sku
  log_analytics_workspace_workspace_id             = module.azure_monitor.log_analytics_workspace_workspace_id
  log_analytics_workspace_primary_key              = module.azure_monitor.log_analytics_workspace_primary_key
  rp_bundle_values                                 = var.rp_bundle_values

  depends_on = [
    module.network,
    module.azure_monitor,
    azurerm_key_vault.kv,
    azurerm_key_vault_access_policy.deployer
  ]
}
