data "azurerm_subscription" "current" {}

data "azurerm_client_config" "current" {}

# Random unique id
resource "random_string" "unique_id" {
  length      = 4
  min_numeric = 4
}

locals {
  service_id                                = random_string.unique_id.result
  workspace_resource_group                  = "rg-${var.workspace_id}"
}
