variable "tre_id" {
  type        = string
  description = "Unique identifier for the TRE, such as projectx-dev-1234"
  validation {
    condition     = length(var.tre_id) < 12
    error_message = "The tre_id value must be < 12 chars."
  }
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
