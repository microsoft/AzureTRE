# Airlock review VMs are ephemeral and use random credentials rather than the
# workspace owner's identity.
resource "random_string" "username" {
  length      = 4
  upper       = true
  lower       = true
  numeric     = true
  min_numeric = 1
  min_lower   = 1
  special     = false
}

module "windows_vm" {
  source = "./vm"

  tre_id            = var.tre_id
  workspace_id      = var.workspace_id
  parent_service_id = var.parent_service_id
  tre_resource_id   = var.tre_resource_id

  image            = var.image
  vm_size          = var.vm_size
  image_gallery_id = var.image_gallery_id
  vm_sizes         = local.vm_sizes
  image_details    = local.image_details

  admin_username = random_string.username.result

  nexus_proxy_url   = local.nexus_proxy_url
  extra_custom_data = local.review_data_script

  enable_cmk_encryption = var.enable_cmk_encryption
  key_store_id          = var.key_store_id

  enable_nic_destroy_wait = true

  providers = {
    azurerm = azurerm
    random  = random
    time    = time
  }
}
