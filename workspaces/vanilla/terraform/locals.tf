data "azurerm_subscription" "current" {}

data "azurerm_client_config" "current" {}

# Random unique id
resource "random_string" "unique_id" {
  length      = 4
  min_numeric = 4
}

locals {
  core_resource_name_suffix      = "${var.resource_name_prefix}-${var.environment}-${var.core_id}"
  workspace_resource_name_suffix = "${local.core_resource_name_suffix}-ws-${var.workspace_id}"
}
