variable "workspace_id" {}
variable "tre_id" {}
variable "tre_resource_id" {}

variable "mgmt_acr_name" {}
variable "mgmt_resource_group_name" {}

variable "is_exposed_externally" {
  type        = bool
  description = "Is the webapp available on the public internet"
  default     = false
}
