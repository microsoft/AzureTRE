variable "tre_id" {
  type = string
}

variable "arm_use_msi" {
  type = bool
}

variable "arm_tenant_id" {}
variable "arm_client_id" {}
variable "arm_client_secret" {}

variable "domain_prefix" {
  type = string
}

variable "cert_name" {
  type = string
}

variable "tre_resource_id" {
  type        = string
  description = "Resource ID"
}
