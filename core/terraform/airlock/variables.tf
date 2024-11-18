variable "tre_id" {
  type = string
}
variable "location" {
  type = string
}
variable "resource_group_name" {
  type = string
}
variable "airlock_storage_subnet_id" {
  type = string
}
variable "airlock_events_subnet_id" {
  type = string
}
variable "enable_local_debugging" {
  type = bool
}
variable "myip" {
  type = string
}
variable "api_principal_id" {
  type = string
}

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

variable "airlock_processor_subnet_id" {
  type = string
}

variable "applicationinsights_connection_string" {
  type = string
}
variable "airlock_servicebus" {
  type = object({
    id                                = string
    default_primary_connection_string = string
  })
}
variable "tre_core_tags" {
  type = map(string)
}

variable "enable_malware_scanning" {
  type        = bool
  description = "If False, Airlock requests will skip the malware scanning stage"
}

variable "arm_environment" {
  type = string
}

variable "log_analytics_workspace_id" {
  type = string
}

variable "blob_core_dns_zone_id" {
  type = string
}
variable "file_core_dns_zone_id" {
  type = string
}
variable "queue_core_dns_zone_id" {
  type = string
}
variable "table_core_dns_zone_id" {
  type = string
}

variable "encryption_identity_id" {
  type        = string
  description = "User Managed Identity with permissions to get encryption keys from key vault"
}

variable "enable_cmk_encryption" {
  type        = bool
  description = "A boolean indicating if key vault will be deployed for customer managed key encryption"
}

variable "key_store_id" {
  type        = string
  description = "ID of the Key Vault/HSM to store CMKs in (only used if enable_cmk_encryption is true)"
  default     = null
}

variable "kv_encryption_key_name" {
  type        = string
  description = "Name of Key Vault Encryption Key (only used if enable_cmk_encryption is true)"
}
