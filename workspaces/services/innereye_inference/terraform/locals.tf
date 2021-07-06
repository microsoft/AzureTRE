# Random unique id
resource "random_string" "unique_id" {
  length      = 4
  min_numeric = 4
}

locals {
  service_id                   = random_string.unique_id.result
  service_resource_name_suffix = "${var.tre_id}-ws-${var.workspace_id}-svc-${local.service_id}"
  core_vnet                      = "vnet-${var.tre_id}"
  core_resource_group_name       = "rg-${var.tre_id}"

}

resource "random_uuid" "inference_auth_key" {
}