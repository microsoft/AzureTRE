# This is used for TRE tags validation only.

config {
  call_module_type = "local"
  force = false
}

plugin "azurerm" {
    enabled = true
    version = "0.30.0"
    source  = "github.com/terraform-linters/tflint-ruleset-azurerm"
}

rule "terraform_typed_variables" {
  enabled = false
}

rule "azurerm_resource_missing_tags" {
  enabled = true
  tags = ["tre_id", "tre_workspace_id"]
}

# Disabled: Workspace secrets have a normal lifecycle and need to be deleted with the workspace
rule "azurerm_resources_missing_prevent_destroy" {
  enabled = false
}
