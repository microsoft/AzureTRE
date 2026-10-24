variable "location" {
  type = string
}
variable "tre_id" {
  type = string
}
variable "resource_group_name" {
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
# The workspace owns the identity and the key. A module cannot refer to resources outside it.
variable "encryption_identity_id" {
  type    = string
  default = null
}
variable "encryption_key_id" {
  type    = string
  default = null
}
