variable "workspace_id" {}
variable "tre_id" {}
variable "tre_resource_id" {}
variable "mgmt_resource_group_name" {}
variable "mgmt_acr_name" {}
variable "image_tag" {}


variable "prefix" {
  type    = string
  default = "aaa"
}

variable "environment" {
  type    = string
  default = "dev"
}

variable "omop_password" {
  description = "password for azure sql admin account"
  sensitive   = true
  default     = "W3ShareTech!"
}

variable "cdr_vocab_container_name" {
  description = "The name of the blob container in the CDR storage account that will be used for vocabulary file uploads."
  default     = "vocabularies"
}

/* Application Service Plan */
variable "asp_kind_edition" {
  default = "Linux"
}
variable "asp_sku_tier" {
  default = "Standard"
}
variable "asp_sku_size" {
  default = "S1"
}

variable "broadsea_image" {
  description = "Docker image for OHDSI - Broadsea (Atlas and WebAPI)"
  default     = "broadsea-webtools"
}

# TODO: this should come from ACR
variable "broadsea_image_tag" {
  description = "Docker image tag for OHDSI - Broadsea (Atlas and WebAPI)"
  default     = "latest"
}
