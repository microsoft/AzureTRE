# This is used for TRE tags validation only.

config {
  call_module_type = "local"
  force = false
}

plugin "azurerm" {
    enabled = true
}

rule "azurerm_resource_missing_tags" {
  enabled = true
  tags = ["tre_id", "tre_workspace_id", "tre_workspace_service_id"]
}

rule "azurerm_resources_missing_prevent_destroy" {
  enabled = false
}
