variable "azure_tenant_id" {
  type = string
}

variable "azure_subscription_id" {
  type = string
}

variable "azure_service_principal_client_id" {
  type = string
}

variable "azure_service_principal_password" {
  type = string
}

variable "tre_id" {
  type        = string
  description = "Unique TRE ID"
}

variable "workspace_id" {
  type        = string
  description = "Unique 4-digit workspace ID"
}

variable "location" {
  type        = string
  description = "Azure location (region) for deployment of core TRE services"
}

variable "address_space" {
  type        = string
  description = "VNet address space for the workspace services"
}
