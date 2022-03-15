variable "workspace_id" {}
variable "tre_id" {}

variable "resource_id" {}

variable "mgmt_acr_name" {}
variable "mgmt_resource_group_name" {}

variable "arm_use_msi" {}
variable "arm_tenant_id" {}
variable "arm_client_id" {}
variable "arm_client_secret" {}

variable "is_exposed_externally" {
  type        = bool
  description = "Is the webapp available on the public internet"
  default     = false
}
