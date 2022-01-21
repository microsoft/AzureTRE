variable "tre_id" {
  type        = string
  description = "Unique TRE ID"
}

variable "location" {
  type        = string
  description = "Azure location (region) for deployment of core TRE services"
}

variable "storage_account_name" {
  type        = string
  description = "The name of the storage account to use"
}

variable "storage_account_primary_access_key" {
  type        = string
  description = "The Primary Access Key for the storage account"
}

variable "nexus_storage_limit" {
  type        = number
  description = "Space allocated in GB for the Nexus data in Azure Files Share"
  default     = 1024
}

variable "shared_subnet_id" {
  type        = string
  description = "The ID of the shared subnet in which to create a private endpoint"
}

variable "web_app_subnet_id" {
  type        = string
  description = "The ID of the web app subnet to connect to"
}

variable "private_dns_zone_azurewebsites_id" {
  type        = string
  description = "The ID of the private DNS zone to use for the private endpoint"
}

variable "log_analytics_workspace_id" {
  type        = string
  description = "ID of the Log Analytics workspace for TRE"
}

variable "core_app_service_plan_id" {
  type        = string
  description = "Name of the App Service plan"
}

variable "core_application_insights_instrumentation_key" {
  type        = string
  description = "Instrumentation key for the Core Application Insights"
}

variable "nexus_allowed_fqdns" {
  type        = string
  description = "comma seperated string of allowed FQDNs for Nexus"
  default     = "*pypi.org"
}

variable "firewall_name" {
  type        = string
  description = "Name of the firewall to connect to"
}

variable "firewall_resource_group_name" {
  type        = string
  description = "Name of the firewall to connect to"
}

variable "web_app_subnet_address_prefixes" {
  type        = list(string)
  description = "List of address prefixes for the Web App subnet"
}
