config {
  module = true
  force = false
}

plugin "azurerm" {
    enabled = true
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

rule "azurerm_resource_missing_tags" {
  enabled = true
  tags = ["tre_id"]
}
