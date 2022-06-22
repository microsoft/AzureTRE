locals {

  short_service_id               = substr(var.tre_resource_id, -4, -1)
  short_workspace_id             = substr(var.workspace_id, -4, -1)
  core_resource_group_name       = "rg-${var.tre_id}"
  workspace_resource_name_suffix = "${var.tre_id}-ws-${local.short_workspace_id}"
  service_resource_name_suffix   = "${var.tre_id}-ws-${local.short_workspace_id}-svc-${local.short_service_id}"
  tre_workspace_service_tags = {
    tre_id                   = var.tre_id
    tre_workspace_id         = var.tre_resource_id
    tre_workspace_service_id = var.workspace_id
  }
}
