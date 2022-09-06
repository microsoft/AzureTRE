locals {
  short_service_id               = substr(var.tre_resource_id, -4, -1)
  short_workspace_id             = substr(var.workspace_id, -4, -1)
  short_parent_id                = substr(var.parent_service_id, -4, -1)
  workspace_resource_name_suffix = "${var.tre_id}-ws-${local.short_workspace_id}"
  service_resource_name_suffix   = "${var.tre_id}-ws-${local.short_workspace_id}-svc-${local.short_service_id}"
  vm_name                        = "windowsvm${local.short_service_id}"
  keyvault_name                  = lower("kv-${substr(local.workspace_resource_name_suffix, -20, -1)}")
  storage_name                   = lower(replace("stg${substr(local.workspace_resource_name_suffix, -8, -1)}", "-", ""))
  vm_password_secret_name        = "${local.vm_name}-admin-credentials"
  tre_user_resources_tags = {
    tre_id                   = var.tre_id
    tre_workspace_id         = var.workspace_id
    tre_workspace_service_id = var.parent_service_id
    tre_user_resource_id     = var.tre_resource_id
  }
  nexus_proxy_url = {
    "V1" = "https://nexus-${var.tre_id}.azurewebsites.net",
    "V2" = "https://nexus-${var.tre_id}.${data.azurerm_resource_group.core.location}.cloudapp.azure.com"
  }
  vm_size = {
    "2 CPU | 8GB RAM"   = { value = "Standard_D2s_v5" },
    "4 CPU | 16GB RAM"  = { value = "Standard_D4s_v5" },
    "8 CPU | 32GB RAM"  = { value = "Standard_D8s_v5" },
    "16 CPU | 64GB RAM" = { value = "Standard_D16s_v5" }
  }
  image_ref = {
    "Windows 10" = {
      "publisher"    = "MicrosoftWindowsDesktop"
      "offer"        = "windows-10"
      "sku"          = "20h2-pro-g2"
      "version"      = "latest"
      "conda_config" = false
    },
    "Server 2019 Data Science VM" = {
      "publisher"    = "microsoft-dsvm"
      "offer"        = "dsvm-win-2019"
      "sku"          = "server-2019"
      "version"      = "latest"
      "conda_config" = true
    }
  }
}
