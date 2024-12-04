variable "mgmt_storage_account_name" {
  type        = string
  description = "Storage account created by bootstrap to hold all Terraform state"
}

variable "mgmt_resource_group_name" {
  type        = string
  description = "Shared management resource group"
}

variable "location" {
  type        = string
  description = "Location used for all resources"
}

variable "acr_sku" {
  type        = string
  default     = "Standard"
  description = "Price tier for ACR"
}

variable "acr_name" {
  type        = string
  description = "Name of ACR"
}

variable "enable_cmk_encryption" {
  type        = bool
  description = "A boolean indicating if customer managed keys will be used for encryption of supporting resources"
  default     = false
}

variable "external_key_store_id" {
  type        = string
  description = "ID of external Key Vault to store CMKs in (only required if enable_cmk_encryption is true)"
  default     = null
}

variable "encryption_kv_name" {
  type        = string
  description = "Name of Key Vault for encryption keys, required only if external_key_store_id is not set (only used if enable_cmk_encryption is true)"
  default     = null
}

variable "kv_mgmt_encryption_key_name" {
  type        = string
  description = "Name of Key Vault Encryption Key for management resources (only used if enable_cmk_encryption is true)"
  default     = "tre-encryption-mgmt"
}
