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
