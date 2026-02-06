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

variable "enable_cmk_encryption" {
  type    = bool
  default = false
}

variable "key_store_id" {
  type = string
}

variable "vm_size" {
  type        = string
  description = "The size of the VM to be deployed"
  default     = "Standard_B2ms"
}

variable "mgmt_acr_name" {
  type        = string
  description = "The name of the management ACR"
}

variable "mgmt_resource_group_name" {
  type        = string
  description = "The management resource group name"
}

variable "nexus_image_tag" {
  type        = string
  description = "The tag of the Nexus image to deploy"
  default     = "latest"
}
