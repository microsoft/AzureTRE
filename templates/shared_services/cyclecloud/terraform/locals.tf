locals {
  core_resource_group_name = "rg-${var.tre_id}"
  core_vnet                = "vnet-${var.tre_id}"
  short_service_id         = substr(var.tre_resource_id, -4, -1)
  vm_name                  = "cyclecloud-${local.short_service_id}"
  storage_name             = lower(replace("stgcc${var.tre_id}${local.short_service_id}", "-", ""))
  tre_shared_service_tags = {
    tre_id                = var.tre_id
    tre_shared_service_id = var.tre_resource_id
  }
}
