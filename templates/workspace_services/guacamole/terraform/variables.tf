variable "workspace_id" {
  type        = string
  description = "The workspace ID"
}
variable "aad_authority_url" {
  type        = string
  description = "The Azure AD authority URL"
}
variable "tre_id" {
  type        = string
  description = "The TRE ID"
}
variable "mgmt_resource_group_name" {
  type        = string
  description = "The management resource group name"
}
variable "mgmt_acr_name" {
  type        = string
  description = "The management ACR name"
}
variable "image_name" {
  type        = string
  description = "The Guacamole image name"
}
variable "image_tag" {
  type        = string
  description = "The Guacamole image tag"
}
variable "guac_disable_copy" {
  type        = bool
  description = "Disable copy from the Guacamole workspace"
}
variable "guac_disable_paste" {
  type        = bool
  description = "Disable paste to the Guacamole workspace"
}
variable "guac_enable_drive" {
  type        = bool
  description = "Enable drive redirection"
}
variable "guac_drive_name" {
  type        = string
  description = "The drive name"
}
variable "guac_drive_path" {
  type        = string
  description = "The drive path"
}
variable "guac_disable_download" {
  type        = bool
  description = "Disable download from the Guacamole workspace"
}
variable "guac_disable_upload" {
  type        = bool
  description = "Disable upload to the Guacamole workspace"
}
variable "guac_server_layout" {
  type        = string
  description = "Server keyboard layout"
}
variable "is_exposed_externally" {
  type        = bool
  description = "Is the Guacamole workspace to be exposed externally?"
}
variable "tre_resource_id" {
  type        = string
  description = "The workspace service ID"
}
variable "arm_environment" {
  type        = string
  description = "The ARM cloud environment"
}
variable "workspace_subscription_id" {
  type        = string
  description = "The id of the Azure subscription the workspace is deployed to"
  default     = ""
}
