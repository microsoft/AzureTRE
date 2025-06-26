locals {
  core_resource_group_name = "rg-${var.tre_id}"

  api_driven_application_rule_collection = jsondecode(base64decode(var.api_driven_rule_collections_b64))
  api_driven_network_rule_collection     = jsondecode(base64decode(var.api_driven_network_rule_collections_b64))
}
