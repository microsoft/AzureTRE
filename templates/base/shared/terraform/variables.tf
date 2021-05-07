variable "tre_name" {
  description = "Name of the DRE"
  type        = string
}

variable "tre_id" {
  description = "Globally unique identifier for the DRE"
  type        = string
}
variable "resource_group_prefix" {
  type        = string
  description = "resource group name prefix"
}

variable "location" {
  type        = string
  description = "Azure region for shared_services deployment"
}

variable "tre_dns_suffix" {
  type        = string
  description = "DNS suffix for the environment. E.g. .dre.myorg.com or .drelocal - must have >= 2 labels such as x.drelocal"
  default     = "internal.drelocal"
}
variable "shared_services_vnet_address_space" {
  type        = string
  description = "shared_services Address Space"
}

variable "container_image_tag" {
  type        = string
  description = "The default tag for container images."
  default     = "master"
}
variable "container_registry_dns_name" {
  type        = string
  description = "The DNS name of the container registry containing the image"
  default     = "marcusreg.azurecr.io"
}
variable "container_registry_username" {
  type        = string
  description = "Username that has access to pull the image"
}
variable "container_registry_password" {
  type        = string
  description = "Password that has access to pull the image"
}