variable "tre_id" {}
variable "location" {}
variable "resource_group_name" {}
variable "airlock_storage_subnet_id" {}
variable "airlock_events_subnet_id" {}
variable "enable_local_debugging" {}
variable "myip" {}
variable "api_principal_id" {}

variable "docker_registry_server" {
  type        = string
  description = "Docker registry server"
}

variable "airlock_processor_image_repository" {
  type        = string
  description = "Repository for Airlock processor image"
  default     = "microsoft/azuretre/airlock-processor"
}

variable "mgmt_resource_group_name" {
  type        = string
  description = "Shared management resource group"
}

variable "mgmt_acr_name" {
  type        = string
  description = "Management ACR name"
}

variable "airlock_app_service_plan_sku" {
  type    = string
  default = "P1v3"
}

variable "airlock_processor_subnet_id" {}

variable "applicationinsights_connection_string" {}
variable "airlock_servicebus" {}
variable "tre_core_tags" {}

variable "enable_malware_scanning" {
  type        = bool
  description = "If False, Airlock requests will skip the malware scanning stage"
}

variable "arm_environment" {}

variable "log_analytics_workspace_id" {}

variable "blob_core_dns_zone_id" {}
variable "file_core_dns_zone_id" {}
variable "queue_core_dns_zone_id" {}
variable "table_core_dns_zone_id" {}
