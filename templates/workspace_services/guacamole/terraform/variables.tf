variable "workspace_id" {
  type = string
}
variable "aad_authority_url" {
  type = string
}
variable "tre_id" {
  type = string
}
variable "mgmt_resource_group_name" {
  type = string
}
variable "mgmt_acr_name" {
  type = string
}
variable "image_name" {
  type = string
}
variable "image_tag" {
  type = string
}
variable "guac_disable_copy" {
  type = bool
}
variable "guac_disable_paste" {
  type = bool
}
variable "guac_enable_drive" {
  type = bool
}
variable "guac_drive_name" {
  type = string
}
variable "guac_drive_path" {
  type = string
}
variable "guac_disable_download" {
  type = bool
}
variable "guac_disable_upload" {
  type = bool
}
variable "is_exposed_externally" {
  type = bool
}
variable "tre_resource_id" {
  type = string
}
variable "arm_environment" {
  type = string
}
