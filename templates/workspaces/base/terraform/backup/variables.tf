variable "location" {
  type = string
}
variable "tre_id" {
  type = string
}
variable "resource_group_name" {
  type = string
}
variable "resource_group_id" {
  type = string
}
variable "tre_workspace_tags" {
  type = map(string)
}
variable "tre_resource_id" {
  type = string
}
variable "enable_cmk_encryption" {
  type = bool
}
variable "encryption_key_versionless_id" {
  type    = string
  default = null
}
variable "encryption_identity_id" {
  type    = string
  default = null
}
