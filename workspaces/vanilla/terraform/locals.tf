data "azurerm_subscription" "current" {}

data "azurerm_client_config" "current" {}

# Random unique id
resource "random_string" "unique_id" {
  length      = 4
  min_numeric = 4
}

locals {
  core_vnet                 = "vnet-${var.tre_id}"
  core_resource_group_name  = "rg-${var.tre_id}"
  workspace_resource_name_suffix = "${var.tre_id}-ws-${var.workspace_id}"
}
