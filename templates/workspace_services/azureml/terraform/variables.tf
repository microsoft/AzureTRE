variable "workspace_id" {
  type = string
}
variable "tre_id" {
  type = string
}
variable "tre_resource_id" {
  type = string
}
variable "display_name" {
  type = string
}
variable "description" {
  type = string
}
variable "is_exposed_externally" {
  type = bool
}
variable "address_space" {
  type = string
}
variable "arm_tenant_id" {
  type = string
}
variable "arm_environment" {
  type = string
}
variable "enable_cmk_encryption" {
  type    = bool
  default = false
}
variable "key_store_id" {
  type = string
}
variable "log_analytics_workspace_name" {
  type = string
}
variable "workspace_owners_group_id" {
  type        = string
  description = "Object ID of the workspace owners AAD group"

  validation {
    condition     = length(trimspace(var.workspace_owners_group_id)) > 0
    error_message = "workspace_owners_group_id must be provided; Entra ID workspace groups are required."
  }
}
variable "workspace_researchers_group_id" {
  type        = string
  description = "Object ID of the workspace researchers AAD group"

  validation {
    condition     = length(trimspace(var.workspace_researchers_group_id)) > 0
    error_message = "workspace_researchers_group_id must be provided; Entra ID workspace groups are required."
  }
}
