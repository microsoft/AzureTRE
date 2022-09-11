locals {
  short_service_id               = substr(var.tre_resource_id, -4, -1)
  short_workspace_id             = substr(var.workspace_id, -4, -1)
  short_parent_id                = substr(var.parent_service_id, -4, -1)
  workspace_resource_name_suffix = "${var.tre_id}-ws-${local.short_workspace_id}"
  service_resource_name_suffix   = "${var.tre_id}-ws-${local.short_workspace_id}-svc-${local.short_service_id}"
  vm_name                        = "linuxvm${local.short_service_id}"
  keyvault_name                  = lower("kv-${substr(local.workspace_resource_name_suffix, -20, -1)}")
  storage_name                   = lower(replace("stg${substr(local.workspace_resource_name_suffix, -8, -1)}", "-", ""))
  vm_password_secret_name        = "${local.vm_name}-admin-credentials"
  tre_user_resources_tags = {
    tre_id                   = var.tre_id
    tre_workspace_id         = var.workspace_id
    tre_workspace_service_id = var.parent_service_id
    tre_user_resource_id     = var.tre_resource_id
  }
  nexus_proxy_url = "https://nexus-${var.tre_id}.${data.azurerm_resource_group.core.location}.cloudapp.azure.com"
  vm_size = {
    "2 CPU | 8GB RAM"   = { value = "Standard_D2s_v5" },
    "4 CPU | 16GB RAM"  = { value = "Standard_D4s_v5" },
    "8 CPU | 32GB RAM"  = { value = "Standard_D8s_v5" },
    "16 CPU | 64GB RAM" = { value = "Standard_D16s_v5" }
  }
  image_ref = {
    "Ubuntu 18.04" = {
      "publisher"    = "canonical"
      "offer"        = "ubuntuserver"
      "sku"          = "18_04-lts-gen2"
      "version"      = "latest"
      "install_ui"   = true
      "conda_config" = false
    },
    "Ubuntu 18.04 Data Science VM" = {
      "publisher"    = "microsoft-dsvm"
      "offer"        = "ubuntu-1804"
      "sku"          = "1804-gen2"
      "version"      = "latest"
      "install_ui"   = false
      "conda_config" = true
    }
  }
}
