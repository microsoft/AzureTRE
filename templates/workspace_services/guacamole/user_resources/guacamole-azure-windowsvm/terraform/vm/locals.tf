locals {
  short_service_id               = substr(var.tre_resource_id, -4, -1)
  short_workspace_id             = substr(var.workspace_id, -4, -1)
  short_parent_id                = substr(var.parent_service_id, -4, -1)
  workspace_resource_name_suffix = "${var.tre_id}-ws-${local.short_workspace_id}"
  service_resource_name_suffix   = "${var.tre_id}-ws-${local.short_workspace_id}-svc-${local.short_service_id}"
  vm_name                        = "windowsvm${local.short_service_id}"
  keyvault_name                  = lower("kv-${substr(local.workspace_resource_name_suffix, -20, -1)}")
  vm_password_secret_name        = "${local.vm_name}-admin-credentials"

  tre_user_resources_tags = merge({
    tre_id                   = var.tre_id
    tre_workspace_id         = var.workspace_id
    tre_workspace_service_id = var.parent_service_id
    tre_user_resource_id     = var.tre_resource_id
  }, var.extra_tags)

  # Create local variables to support the VM resource
  selected_image = local.image_details[var.image]
  # selected_image_source_refs is an array to enable easy use of a dynamic block
  selected_image_source_refs = lookup(local.selected_image, "source_image_reference", null) == null ? [] : [local.selected_image.source_image_reference]
  selected_image_source_id   = lookup(local.selected_image, "source_image_name", null) == null ? null : "${var.image_gallery_id}/images/${local.selected_image.source_image_name}"
  secure_boot_enabled        = lookup(local.selected_image, "secure_boot_enabled", false)
  vtpm_enabled               = lookup(local.selected_image, "vtpm_enabled", false)

  image_details = var.image_details
  vm_sizes      = var.vm_sizes

  cmk_name                 = "tre-encryption-${local.workspace_resource_name_suffix}"
  encryption_identity_name = "id-encryption-${var.tre_id}-${local.short_workspace_id}"

  # Bootstrap script: the shared vm_config.ps1 tooling/config, optionally followed
  # by a caller-supplied script (e.g. the airlock review-data download).
  custom_data_b64 = base64encode(join("\r\n", compact([
    templatefile("${path.module}/vm_config.ps1", {
      nexus_proxy_url        = var.nexus_proxy_url
      SharedStorageAccess    = var.shared_storage_access ? 1 : 0
      InstallAzureCli        = var.install_azure_cli ? 1 : 0
      InstallVsCode          = var.install_vscode ? 1 : 0
      InstallStorageExplorer = var.install_storage_explorer ? 1 : 0
      InstallGit             = var.install_git ? 1 : 0
      InstallPythonTools     = var.install_python_tools ? 1 : 0
      InstallRTools          = var.install_r_tools ? 1 : 0
      StorageAccountName     = var.shared_storage_access ? var.storage_account_name : ""
      StorageAccountKey      = var.shared_storage_access ? var.storage_account_key : ""
      StorageAccountFileHost = var.shared_storage_access ? var.storage_account_file_host : ""
      FileShareName          = var.shared_storage_access ? var.file_share_name : ""
      CondaConfig            = local.selected_image.conda_config ? 1 : 0
    }),
    var.extra_custom_data
  ])))
}
