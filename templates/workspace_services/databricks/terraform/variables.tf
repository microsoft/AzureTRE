variable "tre_id" {
  type        = string
  description = "Unique TRE ID"
}

variable "tre_resource_id" {
  type        = string
  description = "Unique TRE Resource ID"
}

variable "workspace_id" {
  type        = string
  description = "Unique TRE WORKSPACE ID"
}

variable "address_space" {
  type        = string
  description = "The address space that is used by the databricks subnets."
}

variable "is_exposed_externally" {
  type        = bool
  description = "If the databricks workspace is exposed externally or not."
}

variable "arm_environment" {
  type = string
}
