variable "state_storage" {
  type        = string
  description = "Storage account created by bootstrap to hold all Terraform state"
}

variable "mgmt_res_group" {
  type        = string
  description = "Shared management resource group"
}

variable "location" {
  type        = string
  description = "Location used for all resources"
}

variable "acr_sku" {
  type = string
  default = "Standard"
  description = "Price tier for ACR"
}

variable "acr_name" {
  type = string
  description = "Name of ACR"
}

variable "deployment_processor_azure_client_id" {
  description = "The client (app) ID of the service principal used for deploying resources"
  type        = string
  sensitive   = true
}

variable "deployment_processor_azure_client_secret" {
  description = "The client secret (app password) of the service principal used for deploying resources"
  type        = string
  sensitive   = true
}
