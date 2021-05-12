variable "resource_name_prefix" {
  type        = string
  description = "Resource name prefix"
}

variable "environment" {
  type        = string
  description = "The stage of the development lifecycle for the workload that the resource supports. Examples: prod, dev, qa, stage, test"
}

variable "location" {
  type        = string
  description = "Azure region for deployment of core TRE services"
}

variable "address_space" {
  type        = string
  description = "Core services VNET Address Space"
}
