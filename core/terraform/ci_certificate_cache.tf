locals {
  ci_certificate_cache_vault_name = "kv-acme-${var.tre_id}"
  ci_resource_processor_bundle_values = merge(var.rp_bundle_values, {
    certificate_cache_vault_name = var.enable_ci_certificate_cache ? local.ci_certificate_cache_vault_name : ""
  })
}

module "ci_certificate_cache" {
  source                          = "./ci_certificate_cache"
  enabled                         = var.enable_ci_certificate_cache
  vault_name                      = local.ci_certificate_cache_vault_name
  location                        = azurerm_resource_group.core.location
  resource_group_name             = azurerm_resource_group.core.name
  tenant_id                       = data.azurerm_client_config.current.tenant_id
  resource_processor_principal_id = try(module.resource_processor_vmss_porter[0].principal_id, "")
  deployer_principal_id           = data.azurerm_client_config.current.object_id
  shared_subnet_id                = module.network.shared_subnet_id
  private_dns_zone_id             = data.azurerm_private_dns_zone.vaultcore.id
  log_analytics_workspace_id      = module.azure_monitor.log_analytics_workspace_id
  purge_protection_enabled        = var.kv_purge_protection_enabled
  tags                            = local.tre_core_tags
}
