# Random unique id
locals {
  short_service_id               = substr(var.tre_resource_id, -4, -1)
  short_workspace_id             = substr(var.workspace_id, -4, -1)
  core_resource_group_name       = "rg-${var.tre_id}"
  workspace_resource_name_suffix = "${var.tre_id}-ws-${local.short_workspace_id}"
  service_resource_name_suffix   = "${var.tre_id}-ws-${local.short_workspace_id}-svc-${local.short_service_id}"
  allowed_urls                   = ["graph.windows.net", "ml.azure.com", "login.microsoftonline.com", "aadcdn.msftauth.net", "graph.microsoft.com", "management.azure.com", "viennaglobal.azurecr.io"]
  allowed_service_tags           = ["Storage.${data.azurerm_resource_group.ws.location}", "AzureContainerRegistry"]
  workspace_name                 = lower("ml-${substr(local.service_resource_name_suffix, -30, -1)}")
  acr_name                       = lower(replace("acr${substr(local.service_resource_name_suffix, -8, -1)}", "-", ""))
  keyvault_name                  = lower("kv-${substr(local.workspace_resource_name_suffix, -20, -1)}")
  storage_name                   = lower(replace("stg${substr(local.workspace_resource_name_suffix, -8, -1)}", "-", ""))
}
