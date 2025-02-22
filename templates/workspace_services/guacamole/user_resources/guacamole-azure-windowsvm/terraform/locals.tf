locals {
  short_service_id               = substr(var.tre_resource_id, -4, -1)
  short_workspace_id             = substr(var.workspace_id, -4, -1)
  short_parent_id                = substr(var.parent_service_id, -4, -1)
  workspace_resource_name_suffix = "${var.tre_id}-ws-${local.short_workspace_id}"
  service_resource_name_suffix   = "${var.tre_id}-ws-${local.short_workspace_id}-svc-${local.short_service_id}"
  vm_name                        = "windowsvm${local.short_service_id}"
  keyvault_name                  = lower("kv-${substr(local.workspace_resource_name_suffix, -20, -1)}")
  storage_name                   = lower(replace("stg${substr(local.workspace_resource_name_suffix, -8, -1)}", "-", ""))
  admin_username = (
    var.admin_username == "" ?
    (length(data.azuread_user.user[0].mail) > 0 && strcontains(data.azuread_user.user[0].user_principal_name, "#EXT#") ?
      substr(element(split("@", data.azuread_user.user[0].mail), 0), 0, 20) :
      substr(element(split("#EXT#", element(split("@", data.azuread_user.user[0].user_principal_name), 0)), 0), 0, 20)
    ) :
    var.admin_username
  )
  vm_password_secret_name = "${local.vm_name}-admin-credentials"
  tre_user_resources_tags = {
    tre_id                   = var.tre_id
    tre_workspace_id         = var.workspace_id
    tre_workspace_service_id = var.parent_service_id
    tre_user_resource_id     = var.tre_resource_id
    tre_user_id              = var.owner_id
    tre_user_username        = var.admin_username == "" ? local.admin_username : var.admin_username
  }
  nexus_proxy_url = "https://nexus-${data.azurerm_public_ip.app_gateway_ip.fqdn}"

  # Load VM SKU/image details from porter.yaml
  porter_yaml   = yamldecode(file("${path.module}/../porter.yaml"))
  vm_sizes      = local.porter_yaml["custom"]["vm_sizes"]
  image_details = local.porter_yaml["custom"]["image_options"]

  # Create local variables to support the VM resource
  selected_image = local.image_details[var.image]
  # selected_image_source_refs is an array to enable easy use of a dynamic block
  selected_image_source_refs = lookup(local.selected_image, "source_image_reference", null) == null ? [] : [local.selected_image.source_image_reference]
  selected_image_source_id   = lookup(local.selected_image, "source_image_name", null) == null ? null : "${var.image_gallery_id}/images/${local.selected_image.source_image_name}"
  secure_boot_enabled        = lookup(local.selected_image, "secure_boot_enabled", false)
  vtpm_enabled               = lookup(local.selected_image, "vtpm_enabled", false)

  cmk_name                 = "tre-encryption-${local.workspace_resource_name_suffix}"
  encryption_identity_name = "id-encryption-${var.tre_id}-${local.short_workspace_id}"
}
