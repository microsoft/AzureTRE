variable "tre_id" {}
variable "location" {}
variable "resource_group_name" {}
variable "shared_subnet_id" {}
variable "enable_local_debugging" {}

variable "docker_registry_server" {
  type        = string
  description = "Docker registry server"
}

variable "airlock_processor_image_repository" {
  type        = string
  description = "Repository for Airlock processor image"
  default     = "microsoft/azuretre/airlock-processor"
}

variable "mgmt_resource_group_name" {
  type        = string
  description = "Shared management resource group"
}

variable "mgmt_acr_name" {
  type        = string
  description = "Management ACR name"
}
