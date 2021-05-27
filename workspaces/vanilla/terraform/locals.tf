data "azurerm_subscription" "current" {}

data "azurerm_client_config" "current" {}

# Random unique id
resource "random_string" "unique_id" {
  length      = 4
  min_numeric = 4
}

locals {
  core_name_and_id          = "${var.core_name}-${var.core_id}"
  core_vnet                 = "vnet-${var.core_name}-${var.core_id}"
  core_resource_group_name  = "rg-${var.core_name}-${var.core_id}"
}
