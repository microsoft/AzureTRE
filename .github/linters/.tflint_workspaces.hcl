# This is used for TRE tags validation only.

config {
  call_module_type = "all"
  force = false
}

plugin "azurerm" {
    enabled = true
}

# disable all other azurerm rules
rule "azurerm_*" {
  enabled = false
}

rule "azurerm_resource_missing_tags" {
  enabled = true
  tags = ["tre_id", "tre_workspace_id"]
}
