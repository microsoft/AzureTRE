data "azurerm_subscription" "current" {}

data "azurerm_client_config" "current" {}

# Random unique id
resource "random_string" "unique_id" {
  length      = 4
  min_numeric = 4
}

locals {
  service_resource_name_suffix = "${var.tre_id}-ws-${var.workspace_id}-svc-${var.service_id}"
  storage_name             = lower(replace("stg${substr(local.service_resource_name_suffix, -8, -1)}", "-", ""))
}
