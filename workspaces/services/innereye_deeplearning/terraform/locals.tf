# Random unique id
resource "random_string" "unique_id" {
  length      = 4
  min_numeric = 4
}

locals {
  service_id                   = random_string.unique_id.result
  service_resource_name_suffix = "${var.tre_id}-ws-${var.workspace_id}-svc-${local.service_id}"
  aml_compute_id = substr("${var.tre_id}${var.workspace_id}${local.service_id}",-12,-1)
  aml_compute_instance_name = "ci-${local.aml_compute_id}"
  aml_compute_cluster_name = "cp-${local.aml_compute_id}"
}
