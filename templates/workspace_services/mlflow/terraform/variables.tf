variable "workspace_id" {
  type = string
}
variable "tre_id" {
  type = string
}
variable "tre_resource_id" {
  type = string
}

variable "mgmt_acr_name" {
  type = string
}
variable "mgmt_resource_group_name" {
  type = string
}

variable "is_exposed_externally" {
  type        = bool
  description = "Is the webapp available on the public internet"
  default     = false
}
variable "arm_environment" {
  type = string
}
