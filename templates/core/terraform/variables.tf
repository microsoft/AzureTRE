variable "resource_name_prefix" {
  type        = string
  description = "Resource name prefix"
}

variable "environment" {
  type        = string
  description = "The stage of the development lifecycle for the workload that the resource supports. Examples: prod, dev, qa, stage, test"
}

variable "tag" {}

variable "location" {
  type        = string
  description = "Azure region for deployment of core TRE services"
}

variable "tre_dns_suffix" {
  type        = string
  description = "DNS suffix for the environment. E.g. .dre.myorg.com or .drelocal - must have >= 2 labels such as x.drelocal"
}

variable "address_space" {
  type        = string
  description = "Core services VNET Address Space"
}
