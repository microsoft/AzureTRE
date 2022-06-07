variable "tre_id" {
  type        = string
  description = "Unique TRE ID"
}

variable "workspace_id" {
  type        = string
  description = "Unique TRE WORKSPACE ID"
}

variable "location" {
  type        = string
  description = "The deployment location."
}

variable "host_subnet_address_space" {
  type        = string
  description = "Address space for the databricks 'host' subnet."
}

variable "container_subnet_address_space" {
  type        = string
  description = "Address space for the databricks 'container' subnet."
}
