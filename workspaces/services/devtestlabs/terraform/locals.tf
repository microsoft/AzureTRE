# Random unique id
resource "random_string" "unique_id" {
  length      = 4
  min_numeric = 4
}


locals {
  service_id                   = random_string.unique_id.result
  service_resource_name_suffix = "${var.tre_id}-ws-${var.workspace_id}-svc-${local.service_id}"
}