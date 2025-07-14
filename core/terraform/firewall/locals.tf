locals {
  firewall_name = "fw-${var.tre_id}"
  firewall_diagnostic_categories_enabled = [
    "AZFWApplicationRule",
    "AZFWApplicationRuleAggregation",
    "AZFWDnsProxy",
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

  firewall_policy_name = "fw-policy-${var.tre_id}"

  default_firewall_sku   = "Standard"
  effective_firewall_sku = coalesce(var.firewall_sku, local.default_firewall_sku)
}
