variable "tre_id" {
  type        = string
  description = "Unique TRE ID"
}

variable "firewall_policy_id" {
  type        = string
  description = "ID of the firewall policy to use"
}

variable "api_driven_rule_collections_b64" {
  type    = string
  default = "W10=" #b64 for []
}

variable "api_driven_network_rule_collections_b64" {
  type    = string
  default = "W10=" #b64 for []
}
