variable "tre_id" {
  type        = string
  description = "Unique TRE ID"
}

variable "location" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "firewall_sku" {
  type    = string
  default = ""
}

variable "firewall_subnet_id" {
  type        = string
  description = "Subnet ID for the firewall"
}

variable "firewall_management_subnet_id" {
  type        = string
  description = "Subnet ID for the firewall management"
}

variable "firewall_force_tunnel_ip" {
  type    = string
  default = ""
}

variable "tre_core_tags" {
  type        = map(string)
  description = "Tags to apply to all resources"
}

variable "microsoft_graph_fqdn" {
  type        = string
  description = "Microsoft Graph FQDN"
}

variable "log_analytics_workspace_id" {
  type = string
}

variable "resource_processor_ip_group_id" {
  type        = string
  description = "Resource Processor IP Group"
}

variable "web_app_ip_group_id" {
  type        = string
  description = "Web App IP Group"
}

variable "airlock_processor_ip_group_id" {
  type        = string
  description = "Airlock Processor IP Group"
}

variable "shared_services_ip_group_id" {
  type        = string
  description = "Shared Services IP Group"
}
