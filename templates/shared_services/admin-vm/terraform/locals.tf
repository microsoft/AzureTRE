locals {
  core_vnet                = "vnet-${var.tre_id}"
  core_resource_group_name = "rg-${var.tre_id}"
  keyvault_name            = "kv-${var.tre_id}"
  tre_shared_service_tags = {
    tre_id                = var.tre_id
    tre_shared_service_id = var.tre_resource_id
  }
  cmk_name                 = "tre-encryption-${var.tre_id}"
  encryption_identity_name = "id-encryption-${var.tre_id}"

  # Load image details from porter.yaml
  porter_yaml   = yamldecode(file("${path.module}/../porter.yaml"))
  image_details = local.porter_yaml["custom"]["image_options"]

  # Create local variables to support the VM resource
  selected_image = local.image_details[var.image]
  # selected_image_source_refs is an array to enable easy use of a dynamic block
  selected_image_source_refs = lookup(local.selected_image, "source_image_reference", null) == null ? [] : [local.selected_image.source_image_reference]
  selected_image_source_id   = lookup(local.selected_image, "source_image_name", null) == null ? null : "${var.image_gallery_id}/images/${local.selected_image.source_image_name}"
  secure_boot_enabled        = lookup(local.selected_image, "secure_boot_enabled", false)
  vtpm_enabled               = lookup(local.selected_image, "vtpm_enabled", false)
}
