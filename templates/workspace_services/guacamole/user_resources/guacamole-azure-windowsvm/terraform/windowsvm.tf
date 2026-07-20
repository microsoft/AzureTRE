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

  admin_username = local.admin_username

  nexus_proxy_url           = local.nexus_proxy_url
  shared_storage_access     = var.shared_storage_access
  install_azure_cli         = var.install_azure_cli
  install_vscode            = var.install_vscode
  install_storage_explorer  = var.install_storage_explorer
  install_git               = var.install_git
  install_python_tools      = var.install_python_tools
  install_r_tools           = var.install_r_tools
  install_pycharm           = var.install_pycharm
  storage_account_name      = data.azurerm_storage_account.stg.name
  storage_account_key       = data.azurerm_storage_account.stg.primary_access_key
  storage_account_file_host = data.azurerm_storage_account.stg.primary_file_host
  file_share_name           = var.shared_storage_name

  enable_cmk_encryption = var.enable_cmk_encryption
  key_store_id          = var.key_store_id

  enable_shutdown_schedule = var.enable_shutdown_schedule
  shutdown_time            = var.shutdown_time
  shutdown_timezone        = var.shutdown_timezone

  extra_tags = {
    tre_user_id       = var.owner_id
    tre_user_username = var.admin_username == "" ? local.admin_username : var.admin_username
  }

  providers = {
    azurerm = azurerm
    random  = random
    time    = time
  }
}
