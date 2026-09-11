variable "workspace_id" {
  type = string
}

variable "tre_id" {
  type = string
}

variable "parent_service_id" {
  type = string
}

variable "tre_resource_id" {
  type = string
}

variable "display_name" {
  type        = string
  description = "The personal desktop display name"
  default     = ""
}

variable "image" {
  type = string
}

variable "vm_size" {
  type = string
}

variable "shared_storage_access" {
  type = bool
}

variable "shared_storage_name" {
  type = string
}

variable "enable_shutdown_schedule" {
  type    = bool
  default = false
}

variable "shutdown_time" {
  type = string
}

variable "shutdown_timezone" {
  type    = string
  default = "UTC"
}

variable "owner_id" {
  type = string
}

variable "auth_client_id" {
  type        = string
  description = "Client ID used to resolve the session-host owner"
}

variable "auth_client_secret" {
  type        = string
  description = "Client secret used to resolve the session-host owner"
  sensitive   = true
}

variable "auth_tenant_id" {
  type        = string
  description = "Tenant containing the session-host owner"
}

variable "azure_environment" {
  type        = string
  description = "Azure CLI cloud name"
  default     = "AzureCloud"
}

variable "admin_username" {
  type = string
}

variable "arm_environment" {
  type = string
}

variable "workspace_subscription_id" {
  type        = string
  description = "The id of the Azure subscription the workspace is deployed to"
  default     = ""
}
