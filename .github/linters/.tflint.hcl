config {
  call_module_type = "local"
  force = false
}

plugin "azurerm" {
    enabled = true
    version = "0.30.0"
    source  = "github.com/terraform-linters/tflint-ruleset-azurerm"
}

rule "terraform_unused_declarations" {
  enabled = true
}

rule "terraform_typed_variables" {
  enabled = true
}

rule "terraform_required_providers" {
  enabled = true
}

rule "terraform_unused_required_providers" {
  enabled = true
}

rule "terraform_naming_convention" {
  enabled = true
}

rule "terraform_standard_module_structure" {
  enabled = true
}

rule "terraform_required_version" {
  enabled = false
}

# Disabled: Workspace secrets have a normal lifecycle and need to be deleted with the workspace
rule "azurerm_resources_missing_prevent_destroy" {
  enabled = false
}
