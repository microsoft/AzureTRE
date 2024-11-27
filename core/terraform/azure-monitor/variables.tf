variable "tre_id" {
  type = string
}
variable "location" {
  type = string
}
variable "resource_group_name" {
  type = string
}
variable "shared_subnet_id" {
  type = string
}
variable "azure_monitor_dns_zone_id" {
  type = string
}
variable "azure_monitor_oms_opinsights_dns_zone_id" {
  type = string
}
variable "azure_monitor_ods_opinsights_dns_zone_id" {
  type = string
}
variable "azure_monitor_agentsvc_dns_zone_id" {
  type = string
}
variable "blob_core_dns_zone_id" {
  type = string
}
variable "tre_core_tags" {
  type = map(string)
}
variable "enable_local_debugging" {
  type = bool
}

variable "encryption_identity_id" {
  type        = string
  description = "User Managed Identity with permissions to get encryption keys from key vault"
}
variable "enable_cmk_encryption" {
  type        = bool
  description = "A boolean indicating if customer managed keys will be used for encryption of supporting resources"
}
variable "key_store_id" {
  type        = string
  description = "ID of the Key Vault to store CMKs in (only used if enable_cmk_encryption is true)"
  default     = null
}
variable "kv_encryption_key_name" {
  type        = string
  description = "Name of Key Vault Encryption Key (only used if enable_cmk_encryption is true)"
}
