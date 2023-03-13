locals {
  short_service_id               = substr(var.tre_resource_id, -4, -1)
  short_workspace_id             = substr(var.workspace_id, -4, -1)
  aad_tenant_id                  = data.azurerm_key_vault_secret.aad_tenant_id.value
  workspace_resource_name_suffix = "${var.tre_id}-ws-${local.short_workspace_id}"
  keyvault_name                  = lower("kv-${substr(local.workspace_resource_name_suffix, -20, -1)}")
  service_resource_name_suffix   = "${local.short_workspace_id}svc${local.short_service_id}"
  authority                      = "${var.aad_authority_url}/${local.aad_tenant_id}"
  core_resource_group_name       = "rg-${var.tre_id}"
  workspace_service_tags = {
    tre_id                   = var.tre_id
    tre_workspace_id         = var.workspace_id
    tre_workspace_service_id = var.tre_resource_id
  }
}
