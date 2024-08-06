locals {
  short_workspace_id = substr(var.tre_resource_id, -4, -1)
  app_insights_name  = "appi-${var.tre_id}-ws-${local.short_workspace_id}"
}
