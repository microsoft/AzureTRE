variable "tre_id" {
  type        = string
  description = "Unique TRE ID"
}

variable "microsoft_graph_fqdn" {
  type        = string
  description = "Microsoft Graph FQDN"
}

variable "tre_resource_id" {
  type        = string
  description = "Resource ID"
}

variable "api_driven_rule_collections_b64" {
  type    = string
  default = "W10=" #b64 for []
}

variable "api_driven_network_rule_collections_b64" {
  type    = string
  default = "W10=" #b64 for []
}

variable "firewall_sku" {
  type    = string
  default = ""
}
