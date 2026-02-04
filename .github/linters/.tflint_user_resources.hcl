# This is used for TRE tags validation only.

config {
  call_module_type = "none"
  force = false
}

plugin "azurerm" {
    enabled = true
    version = "0.30.0"
    source  = "github.com/terraform-linters/tflint-ruleset-azurerm"
}

# disable all other azurerm rules
rule "azurerm_*" {
  enabled = false
}

rule "azurerm_resource_missing_tags" {
  enabled = true
  tags = ["tre_id", "tre_workspace_id", "tre_workspace_service_id", "tre_user_resource_id"]
}
