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

variable "management_api_image_repository" {
  type        = string
  description = "Repository for management API image"
  default     = "microsoft/azuretre/management-api"
}

variable "management_api_image_tag" {
  type        = string
  description = "Tag for management API image"
  default     = "main-latest"
}

variable "docker_registry_server" {
  type        = string
  description = "Docker registry server"
}

variable "docker_registry_username" {
  type        = string
  description = "Docker registry username"
}

variable "docker_registry_password" {
  type        = string
  description = "Docker registry password"
}
