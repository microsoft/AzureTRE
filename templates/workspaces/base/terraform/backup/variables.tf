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
variable "enable_local_debugging" {
  type = bool
}
variable "tre_workspace_tags" {
  type = map(string)
}
variable "arm_environment" {
  type = string
}
variable "azurerm_storage_account_id" {
  type = string
}
variable "tre_resource_id" {
  type = string
}
variable "enable_cmk_encryption" {
  type = bool
}
variable "shared_storage_name" {
  type = string
}
