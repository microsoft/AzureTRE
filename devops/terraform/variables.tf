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

variable "resource_name_prefix" {
  type        = string
  description = "Prefix appended to all resources"
}

variable "acr_sku" {
  type = string
  default = "Standard"
  description = "Price tier for ACR"
}