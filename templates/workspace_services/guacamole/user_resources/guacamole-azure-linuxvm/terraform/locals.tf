locals {
  ws_unique_identifier_suffix            = length(var.parent_ws_unique_identifier_suffix) <= 4 ? substr(var.workspace_id, -4, -1) : var.parent_ws_unique_identifier_suffix
  svc_unique_identifier_suffix           = length(var.parent_ws_svc_unique_identifier_suffix) <= 4 ? substr(var.parent_service_id, -4, -1) : var.parent_ws_svc_unique_identifier_suffix
  user_resource_unique_identifier_suffix = length(var.parent_ws_unique_identifier_suffix) <= 4 ? substr(var.tre_resource_id, -4, -1) : substr(var.tre_resource_id, -6, -1)
  workspace_resource_name_suffix         = "${var.tre_id}-ws-${local.ws_unique_identifier_suffix}"
  service_resource_name_suffix           = "${var.tre_id}-ws-${local.ws_unique_identifier_suffix}-svc-${local.svc_unique_identifier_suffix}"
  vm_name                                = "linuxvm${local.user_resource_unique_identifier_suffix}"
  keyvault_name                          = lower("kv-${substr(local.workspace_resource_name_suffix, length(var.parent_ws_unique_identifier_suffix) <= 4 ? -20 : -22, -1)}")
  storage_name                           = lower(replace("stg${substr(local.workspace_resource_name_suffix, length(var.parent_ws_unique_identifier_suffix) <= 4 ? -8 : -10, -1)}", "-", ""))
  vm_password_secret_name                = "${local.vm_name}-admin-credentials"
  tre_user_resources_tags = {
    tre_id                   = var.tre_id
    tre_workspace_id         = var.workspace_id
    tre_workspace_service_id = var.parent_service_id
    tre_user_resource_id     = var.tre_resource_id
  }
  nexus_proxy_url = "https://nexus-${var.tre_id}.${data.azurerm_resource_group.core.location}.cloudapp.azure.com"

  # Load VM SKU/image details from porter.yaml
  porter_yaml   = yamldecode(file("${path.module}/../porter.yaml"))
  vm_sizes      = local.porter_yaml["custom"]["vm_sizes"]
  image_details = local.porter_yaml["custom"]["image_options"]

  # Create local variables to support the VM resource
  selected_image = local.image_details[var.image]
  # selected_image_source_refs is an array to enable easy use of a dynamic block
  selected_image_source_refs = lookup(local.selected_image, "source_image_reference", null) == null ? [] : [local.selected_image.source_image_reference]
  selected_image_source_id   = lookup(local.selected_image, "source_image_name", null) == null ? null : "${var.image_gallery_id}/images/${local.selected_image.source_image_name}"
}
