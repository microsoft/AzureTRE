locals {
  core_resource_group_name = "rg-${var.tre_id}"
  firewall_name            = "fw-${var.tre_id}"
  firewall_diagnostic_categories_enabled = [
    "AZFWApplicationRule",
    "AZFWApplicationRuleAggregation",
    "AZFWDnsQuery",
    "AZFWFatFlow",
    "AZFWFlowTrace",
    "AZFWIdpsSignature",
    "AZFWInternalFqdnResolutionFailure",
    "AZFWNatRule",
    "AZFWNatRuleAggregation",
    "AZFWNetworkRule",
    "AZFWNetworkRuleAggregation",
    "AZFWThreatIntel"
  ]
  tre_shared_service_tags = {
    tre_id                = var.tre_id
    tre_shared_service_id = var.tre_resource_id
  }

  api_driven_application_rule_collection = jsondecode(base64decode(var.api_driven_rule_collections_b64))
  api_driven_network_rule_collection     = jsondecode(base64decode(var.api_driven_network_rule_collections_b64))

  firewall_policy_name = "fw-policy-${var.tre_id}"

  default_firewall_sku   = "Standard"
  effective_firewall_sku = coalesce(var.firewall_sku, local.default_firewall_sku)
}
