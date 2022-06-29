variable "workspace_id" {}
variable "tre_id" {}
variable "arm_client_id" {}
variable "arm_client_secret" {}
variable "arm_tenant_id" {}
variable "arm_use_msi" {}
variable "mgmt_resource_group_name" {}
variable "mgmt_acr_name" {}
variable "image_name" {}
variable "image_tag" {}
variable "guac_disable_copy" {}
variable "guac_disable_paste" {}
variable "guac_enable_drive" {}
variable "guac_drive_name" {}
variable "guac_drive_path" {}
variable "guac_disable_download" {}
variable "is_exposed_externally" {}
variable "tre_resource_id" {}
variable "workspace_identifier_uri" {
  type = string
  validation {
    condition = can(regex("^api://[a-zA-Z0-9_.-]*", var.workspace_identifier_uri))
    error_message = "Uri should be in the form of: api://some-chars-and-or-numbers."
  }
}
