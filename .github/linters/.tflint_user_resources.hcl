# This is used for TRE tags validation only.

config {
  module = true
  force = false
}

plugin "azurerm" {
    enabled = true
}

rule "azurerm_resource_missing_tags" {
  enabled = true
  tags = ["tre_id", "tre_workspace_id", "tre_workspace_service_id", "tre_user_resource_id"]
}
