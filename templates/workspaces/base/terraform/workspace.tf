resource "azurerm_resource_group" "ws" {
  location = var.location
  name     = "rg-${local.workspace_resource_name_suffix}"
  tags = merge(
    local.tre_workspace_tags,
    {
      project = "Azure Trusted Research Environment",
      source  = "https://github.com/microsoft/AzureTRE/"
    },
  )

  lifecycle { ignore_changes = [tags] }
}

// Networking is causing dependencies issues when some parts are deployed from
// Azure, especially for storage shares. It became quite difficult to figure out the needed
// dependencies for each resource seperatly, so to make it easier we packed all network
// resources as a single module that should be depended on.
module "network" {
  source                 = "./network"
  location               = var.location
  tre_id                 = var.tre_id
  address_spaces         = var.address_spaces
  ws_resource_group_name = azurerm_resource_group.ws.name
  tre_resource_id        = var.tre_resource_id
  tre_workspace_tags     = local.tre_workspace_tags
  arm_use_msi            = var.arm_use_msi
  arm_tenant_id          = var.arm_tenant_id
  arm_client_id          = var.arm_client_id
  arm_client_secret      = var.arm_client_secret
}

module "aad" {
  source                         = "./aad"
  tre_workspace_tags             = local.tre_workspace_tags
  count                          = var.register_aad_application ? 1 : 0
  key_vault_id                   = azurerm_key_vault.kv.id
  workspace_resource_name_suffix = local.workspace_resource_name_suffix
  workspace_owner_object_id      = var.workspace_owner_object_id
  aad_redirect_uris_b64          = var.aad_redirect_uris_b64
  create_aad_groups              = var.create_aad_groups

  depends_on = [
    azurerm_key_vault_access_policy.deployer,
    azurerm_key_vault_access_policy.resource_processor,
    null_resource.wait_for_dns_vault
  ]
}

module "airlock" {
  count                       = var.enable_airlock ? 1 : 0
  source                      = "./airlock"
  location                    = var.location
  tre_id                      = var.tre_id
  tre_workspace_tags          = local.tre_workspace_tags
  ws_resource_group_name      = azurerm_resource_group.ws.name
  enable_local_debugging      = var.enable_local_debugging
  services_subnet_id          = module.network.services_subnet_id
  short_workspace_id          = local.short_workspace_id
  airlock_processor_subnet_id = module.network.airlock_processor_subnet_id
  depends_on = [
    module.network,
  ]
}


module "azure_monitor" {
  source                                   = "./azure-monitor"
  tre_id                                   = var.tre_id
  location                                 = var.location
  resource_group_name                      = azurerm_resource_group.ws.name
  resource_group_id                        = azurerm_resource_group.ws.id
  tre_resource_id                          = var.tre_resource_id
  tre_workspace_tags                       = local.tre_workspace_tags
  workspace_subnet_id                      = module.network.services_subnet_id
  azure_monitor_dns_zone_id                = module.network.azure_monitor_dns_zone_id
  azure_monitor_oms_opinsights_dns_zone_id = module.network.azure_monitor_oms_opinsights_dns_zone_id
  azure_monitor_ods_opinsights_dns_zone_id = module.network.azure_monitor_ods_opinsights_dns_zone_id
  azure_monitor_agentsvc_dns_zone_id       = module.network.azure_monitor_agentsvc_dns_zone_id
  blob_core_dns_zone_id                    = module.network.blobcore_zone_id
  enable_local_debugging                   = var.enable_local_debugging
  depends_on = [
    module.network,
    module.airlock
  ]
}
