variable "tre_id" {
  type = string
}

variable "tre_resource_id" {
  type        = string
  description = "Resource ID"
}

variable "ssl_cert_name" {
  type = string
}

variable "mgmt_resource_group_name" {
  type        = string
  description = "Shared management resource group"
}

variable "acr_name" {
  type        = string
  description = "Name of Azure Container Registry"
}
