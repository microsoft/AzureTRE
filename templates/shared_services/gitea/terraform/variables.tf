variable "tre_id" {
  type        = string
  description = "Unique TRE ID"
}

variable "location" {
  type        = string
  description = "Azure location (region) for deployment of core TRE services"
}

variable "docker_registry_server" {
  type        = string
  description = "Docker registry server"
}

variable "keyvault_id" {
  type = string
}

variable "acr_id" {
  type = string
}

variable "storage_account_name" {
  type        = string
  description = "The name of the storage account to use"
}

variable "storage_account_primary_access_key" {
  type        = string
  description = "The Primary Access Key for the storage account"
}

variable "shared_subnet_id" {
  type        = string
  description = "The ID of the shared subnet in which to create a private endpoint"
}

variable "web_app_subnet_id" {
  type        = string
  description = "The ID of the Web App subnet to connect to"
}

variable "private_dns_zone_azurewebsites_id" {
  type        = string
  description = "The ID of the private DNS zone to use for the private endpoint"
}

variable "private_dns_zone_mysql_id" {
  type        = string
  description = "The ID of the private DNS zone for MySQL"
}

variable "gitea_storage_limit" {
  type        = number
  description = "Space allocated in GB for the Gitea data in Azure Files Share"
  default     = 1024
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
