variable "tre_id" {
  type        = string
  description = "Unique TRE ID"
}

variable "firewall_policy_id" {
  type        = string
  description = "ID of the firewall policy to use"
}

variable "api_driven_rule_collections_file" {
  type        = string
  description = "Path to the base64-encoded application rule collections file"
}

variable "api_driven_network_rule_collections_file" {
  type        = string
  description = "Path to the base64-encoded network rule collections file"
}
