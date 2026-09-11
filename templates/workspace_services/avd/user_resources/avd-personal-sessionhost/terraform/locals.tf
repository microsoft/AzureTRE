locals {
  short_service_id               = substr(var.tre_resource_id, -4, -1)
  short_workspace_id             = substr(var.workspace_id, -4, -1)
  short_parent_id                = substr(var.parent_service_id, -4, -1)
  workspace_resource_name_suffix = "${var.tre_id}-ws-${local.short_workspace_id}"
  service_resource_name_suffix   = "${var.tre_id}-ws-${local.short_workspace_id}-svc-${local.short_service_id}"
  vm_name                        = "avd${local.short_workspace_id}${local.short_parent_id}${local.short_service_id}"
  keyvault_name                  = lower("kv-${substr(local.workspace_resource_name_suffix, -20, -1)}")
  storage_name                   = lower(replace("stg${substr(local.workspace_resource_name_suffix, -8, -1)}", "-", ""))

  admin_username = var.admin_username == "" ? "avduser${substr(replace(var.owner_id, "-", ""), 0, 8)}" : var.admin_username

  vm_password_secret_name = "${local.vm_name}-admin-credentials"

  clipboard_server_to_client = contains(["session_to_client", "both"], data.azurerm_key_vault_secret.clipboard_transfer_direction.value) ? 4 : 0
  clipboard_client_to_server = contains(["client_to_session", "both"], data.azurerm_key_vault_secret.clipboard_transfer_direction.value) ? 4 : 0
  avd_dsc_artifact_url       = "${data.azurerm_storage_account.stg.primary_blob_endpoint}${azurerm_storage_container.avd_artifacts.name}/Configuration.zip"
  avd_dsc_artifact_sha256    = split(" ", trimspace(file("${path.module}/../Configuration.zip.sha256")))[0]
  mount_storage_command      = var.shared_storage_access ? "$storageCredential = [pscredential]::new('localhost\\${data.azurerm_storage_account.stg.name}', (ConvertTo-SecureString '${data.azurerm_storage_account.stg.primary_access_key}' -AsPlainText -Force)); if (!(Get-SmbGlobalMapping -LocalPath 'Z:' -ErrorAction SilentlyContinue)) { New-SmbGlobalMapping -LocalPath 'Z:' -RemotePath '\\\\${data.azurerm_storage_account.stg.primary_file_host}\\${var.shared_storage_name}' -Credential $storageCredential -Persistent $true -RequirePrivacy $true -ErrorAction Stop }; if (!(Test-Path 'Z:\\')) { throw 'Workspace shared storage is not accessible' }" : ""
  owner_user_principal_name  = data.azuread_user.owner.user_principal_name

  tre_user_resources_tags = {
    tre_id                   = var.tre_id
    tre_workspace_id         = var.workspace_id
    tre_workspace_service_id = var.parent_service_id
    tre_user_resource_id     = var.tre_resource_id
    tre_user_id              = var.owner_id
    tre_user_username        = var.admin_username == "" ? local.admin_username : var.admin_username
  }

  # Load VM SKU/image details from porter.yaml
  porter_yaml   = yamldecode(file("${path.module}/../porter.yaml"))
  vm_sizes      = local.porter_yaml["custom"]["vm_sizes"]
  image_details = local.porter_yaml["custom"]["image_options"]

  # Create local variables to support the VM resource
  selected_image = local.image_details[var.image]
  # selected_image_source_refs is an array to enable easy use of a dynamic block
  selected_image_source_refs = lookup(local.selected_image, "source_image_reference", null) == null ? [] : [local.selected_image.source_image_reference]
  secure_boot_enabled        = lookup(local.selected_image, "secure_boot_enabled", false)
  vtpm_enabled               = lookup(local.selected_image, "vtpm_enabled", false)
}
