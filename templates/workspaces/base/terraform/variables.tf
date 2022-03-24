variable "tre_id" {
  type        = string
  description = "Unique TRE ID"
}

variable "tre_resource_id" {
  type        = string
  description = "Resource ID"
}

variable "shared_storage_quota" {
  type        = number
  default     = 50
  description = "Quota (in GB) to set for the VM Shared Storage."
}

variable "location" {
  type        = string
  description = "Azure location (region) for deployment of core TRE services"
}

variable "address_space" {
  type        = string
  description = "VNet address space for the workspace services"
}

variable "deploy_app_service_plan" {
  type        = bool
  default     = true
  description = "Deploy app service plan"
}

variable "app_service_plan_sku" {
  type        = string
  default     = "P1v3"
  description = "App Service Plan SKU"
}

variable "enable_local_debugging" {
  type        = bool
  default     = false
  description = "This will allow storage account access over the internet. Set to true to allow deploying this from a local machine."
}
