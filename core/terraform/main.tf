# Azure Provider source and version being used
terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "= 4.27.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "= 3.7.2"
    }
    local = {
      source  = "hashicorp/local"
      version = "= 2.5.2"
    }
    http = {
      source  = "hashicorp/http"
      version = "= 3.5.0"
    }
    azapi = {
      source  = "Azure/azapi"
      version = "= 2.3.0"
    }
  }

  backend "azurerm" {}
}

provider "azapi" {
  use_msi = var.arm_use_msi
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
  enable_cmk_encryption                    = var.enable_cmk_encryption
  encryption_key_versionless_id            = var.enable_cmk_encryption ? azurerm_key_vault_key.tre_encryption[0].versionless_id : null
  encryption_identity_id                   = var.enable_cmk_encryption ? azurerm_user_assigned_identity.encryption[0].id : null

  depends_on = [
    module.network,
    azurerm_key_vault_key.tre_encryption[0]
  ]
}

module "network" {
  source              = "./network"
  tre_id              = var.tre_id
  location            = var.location
  resource_group_name = azurerm_resource_group.core.name
  core_address_space  = var.core_address_space
  arm_environment     = var.arm_environment
}

module "firewall" {
  source                         = "./firewall"
  tre_id                         = var.tre_id
  firewall_sku                   = var.firewall_sku
  firewall_subnet_id             = module.network.azure_firewall_subnet_id
  firewall_force_tunnel_ip       = var.firewall_force_tunnel_ip
  location                       = var.location
  resource_group_name            = azurerm_resource_group.core.name
  tre_core_tags                  = local.tre_core_tags
  microsoft_graph_fqdn           = regex("(?:(?P<scheme>[^:/?#]+):)?(?://(?P<fqdn>[^/?#:]*))?", module.terraform_azurerm_environment_configuration.microsoft_graph_endpoint).fqdn
  log_analytics_workspace_id     = module.azure_monitor.log_analytics_workspace_id
  firewall_management_subnet_id  = module.network.firewall_management_subnet_id
  resource_processor_ip_group_id = module.network.resource_processor_ip_group_id
  shared_services_ip_group_id    = module.network.shared_services_ip_group_id
  web_app_ip_group_id            = module.network.web_app_ip_group_id
  airlock_processor_ip_group_id  = module.network.airlock_processor_ip_group_id
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
  app_gateway_sku            = var.app_gateway_sku
  deployer_principal_id      = data.azurerm_client_config.current.object_id

  enable_cmk_encryption         = var.enable_cmk_encryption
  encryption_key_versionless_id = var.enable_cmk_encryption ? azurerm_key_vault_key.tre_encryption[0].versionless_id : null
  encryption_identity_id        = var.enable_cmk_encryption ? azurerm_user_assigned_identity.encryption[0].id : null

  depends_on = [
    module.network,
    azurerm_key_vault.kv,
    azurerm_role_assignment.keyvault_deployer_role,
    azurerm_private_endpoint.api_private_endpoint,
    azurerm_key_vault_key.tre_encryption[0]
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
  acr_id                                = data.azurerm_container_registry.acr.id
  api_principal_id                      = azurerm_user_assigned_identity.id.principal_id
  airlock_app_service_plan_sku          = var.core_app_service_plan_sku
  airlock_processor_subnet_id           = module.network.airlock_processor_subnet_id
  airlock_servicebus                    = azurerm_servicebus_namespace.sb
  airlock_servicebus_fqdn               = azurerm_servicebus_namespace.sb.endpoint
  applicationinsights_connection_string = module.azure_monitor.app_insights_connection_string
  enable_malware_scanning               = var.enable_airlock_malware_scanning
  arm_environment                       = var.arm_environment
  tre_core_tags                         = local.tre_core_tags
  log_analytics_workspace_id            = module.azure_monitor.log_analytics_workspace_id
  blob_core_dns_zone_id                 = module.network.blob_core_dns_zone_id
  file_core_dns_zone_id                 = module.network.file_core_dns_zone_id
  queue_core_dns_zone_id                = module.network.queue_core_dns_zone_id
  table_core_dns_zone_id                = module.network.table_core_dns_zone_id
  eventgrid_private_dns_zone_id         = module.network.eventgrid_private_dns_zone_id

  enable_local_debugging        = var.enable_local_debugging
  myip                          = local.myip
  enable_cmk_encryption         = var.enable_cmk_encryption
  encryption_key_versionless_id = var.enable_cmk_encryption ? azurerm_key_vault_key.tre_encryption[0].versionless_id : null
  encryption_identity_id        = var.enable_cmk_encryption ? azurerm_user_assigned_identity.encryption[0].id : null

  depends_on = [
    azurerm_servicebus_namespace.sb,
    module.network,
    azurerm_key_vault_key.tre_encryption[0]
  ]
}

module "resource_processor_vmss_porter" {
  count                                            = var.resource_processor_type == "vmss_porter" ? 1 : 0
  source                                           = "./resource_processor/vmss_porter"
  tre_id                                           = var.tre_id
  location                                         = var.location
  resource_group_name                              = azurerm_resource_group.core.name
  core_api_client_id                               = var.api_client_id
  acr_id                                           = data.azurerm_container_registry.mgmt_acr.id
  app_insights_connection_string                   = module.azure_monitor.app_insights_connection_string
  resource_processor_subnet_id                     = module.network.resource_processor_subnet_id
  blob_core_dns_zone_id                            = module.network.blob_core_dns_zone_id
  docker_registry_server                           = local.docker_registry_server
  resource_processor_vmss_porter_image_repository  = var.resource_processor_vmss_porter_image_repository
  service_bus_namespace_id                         = azurerm_servicebus_namespace.sb.id
  service_bus_namespace_fqdn                       = local.service_bus_namespace_fqdn
  service_bus_resource_request_queue               = azurerm_servicebus_queue.workspacequeue.name
  service_bus_deployment_status_update_queue       = azurerm_servicebus_queue.service_bus_deployment_status_update_queue.name
  mgmt_storage_account_name                        = var.mgmt_storage_account_name
  mgmt_storage_account_id                          = data.azurerm_storage_account.mgmt_storage.id
  mgmt_resource_group_name                         = var.mgmt_resource_group_name
  terraform_state_container_name                   = var.terraform_state_container_name
  key_vault_name                                   = azurerm_key_vault.kv.name
  key_vault_url                                    = azurerm_key_vault.kv.vault_uri
  key_vault_id                                     = azurerm_key_vault.kv.id
  subscription_id                                  = var.arm_subscription_id
  resource_processor_number_processes_per_instance = var.resource_processor_number_processes_per_instance
  resource_processor_vmss_sku                      = var.resource_processor_vmss_sku
  arm_environment                                  = var.arm_environment
  logging_level                                    = var.logging_level
  rp_bundle_values                                 = var.rp_bundle_values
  enable_cmk_encryption                            = var.enable_cmk_encryption
  key_store_id                                     = local.key_store_id
  kv_encryption_key_name                           = local.cmk_name
  ui_client_id                                     = var.swagger_ui_client_id
  auto_grant_workspace_consent                     = var.auto_grant_workspace_consent
  enable_airlock_malware_scanning                  = var.enable_airlock_malware_scanning
  airlock_malware_scan_result_topic_name           = module.airlock_resources.airlock_malware_scan_result_topic_name
  firewall_policy_id                               = module.firewall.firewall_policy_id

  depends_on = [
    module.network,
    module.azure_monitor,
    azurerm_key_vault.kv,
    azurerm_role_assignment.keyvault_deployer_role,
    azurerm_key_vault_key.tre_encryption[0]
  ]
}

module "terraform_azurerm_environment_configuration" {
  source          = "git::https://github.com/microsoft/terraform-azurerm-environment-configuration.git?ref=0.6.0"
  arm_environment = var.arm_environment
}
