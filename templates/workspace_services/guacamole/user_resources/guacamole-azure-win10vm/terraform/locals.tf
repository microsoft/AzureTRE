locals {
  short_service_id             = substr(var.tre_resource_id, -4, -1)
  short_workspace_id           = substr(var.workspace_id, -4, -1)
  short_parent_id              = substr(var.parent_service_id, -4, -1)
  service_resource_name_suffix = "${var.tre_id}-ws-${local.short_workspace_id}-svc-${local.short_service_id}"
  core_vnet                    = "vnet-${var.tre_id}"
  core_resource_group_name     = "rg-${var.tre_id}"
  vm_name                      = "win10vm${local.short_service_id}"
}
