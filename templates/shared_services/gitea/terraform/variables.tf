# variable "gitea_image_repository" {}
# variable "gitea_image_tag" {}
# variable "docker_registry_server" {}
# variable "docker_registry_username" {}
# variable "docker_registry_password" {}

variable "tre_id" {
  type        = string
  description = "Unique TRE ID"
}


variable "location" {
  type        = string
  description = "Azure location (region) for deployment of core TRE services"
}
