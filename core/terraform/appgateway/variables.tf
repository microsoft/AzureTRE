
variable "tre_id" {
  type = string
}
variable "location" {
  type = string
}
variable "resource_group_name" {
  type = string
}
variable "app_gw_subnet" {
  type = string
}
variable "shared_subnet" {
  type = string
}
variable "api_fqdn" {
  type = string
}
variable "keyvault_id" {
  type = string
}
variable "static_web_dns_zone_id" {
  type = string
}
variable "log_analytics_workspace_id" {
  type = string
}
variable "mgmt_resource_group_name" {
  type = string
}
variable "encryption_identity_id" {
  type        = string
  description = "User Managed Identity with permissions to get encryption keys from key vault"
}
variable "enable_cmk_encryption" {
  type        = bool
  description = "A boolean indicating if key vault will be deployed for customer managed key encryption"
}
variable "kv_name" {
  type        = string
  description = "Name of Key Vault (only used if enable_cmk_encryption is true)"
}
variable "kv_encryption_key_name" {
  type        = string
  description = "Name of Key Vault Encryption Key (only used if enable_cmk_encryption is true)"
}
