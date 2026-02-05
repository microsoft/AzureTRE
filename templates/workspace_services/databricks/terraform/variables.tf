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

variable "workspace_owners_group_id" {
  type        = string
  description = "The object ID of the Entra ID group for TRE workspace owners"
  validation {
    condition     = length(trimspace(var.workspace_owners_group_id)) > 0
    error_message = "workspace_owners_group_id must be provided; Entra ID workspace groups are required."
  }
}

variable "workspace_researchers_group_id" {
  type        = string
  description = "The object ID of the Entra ID group for TRE workspace researchers"
  validation {
    condition     = length(trimspace(var.workspace_researchers_group_id)) > 0
    error_message = "workspace_researchers_group_id must be provided; Entra ID workspace groups are required."
  }
}
