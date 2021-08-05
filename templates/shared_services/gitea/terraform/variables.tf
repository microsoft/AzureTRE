variable "tre_id" {
  type        = string
  description = "Unique TRE ID"
}


variable "location" {
  type        = string
  description = "Azure location (region) for deployment of core TRE services"
}

variable "image_tag" {
  type        = string
  description = "Tag for Gitea image"
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
  sensitive   = true
}

variable "keyvault_id" {}