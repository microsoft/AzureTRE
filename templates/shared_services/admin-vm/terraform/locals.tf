locals {
  core_vnet                = "vnet-${var.tre_id}"
  core_resource_group_name = "rg-${var.tre_id}"
  keyvault_name            = "kv-${var.tre_id}"

  tre_shared_service_tags = merge(
    var.tags, {
      tre_id                = var.tre_id
      tre_shared_service_id = var.tre_resource_id
    }
  )
}
