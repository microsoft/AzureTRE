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

variable "firewall_force_tunnel_ip" {
  type    = string
  default = ""
}

variable "firewall_dns_proxy_enabled" {
  type        = bool
  default     = true
  description = "Enable DNS proxy on the firewall policy. Required for spoke VNets that point at the firewall IP for DNS to reach Azure DNS and linked private DNS zones."
}

variable "firewall_dns_servers" {
  type        = list(string)
  default     = []
  description = "Upstream DNS servers used by the firewall when proxy is enabled. Empty list = Azure-provided DNS."
}
