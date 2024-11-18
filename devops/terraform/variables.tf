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

variable "kv_purge_protection_enabled" {
  type        = bool
  description = "A boolean indicating if the purge protection will be enabled on the core keyvault."
  default     = true
}

variable "enable_cmk_encryption" {
  type        = bool
  description = "A boolean indicating if key vault will be deployed for customer managed key encryption"
  default     = false
}

variable "external_key_store_id" {
  type        = string
  description = "ID of external Key Vault/HSM to store CMKs in (only required if enable_cmk_encryption is true)"
  default     = null
}

variable "encryption_kv_name" {
  type        = string
  description = "Name of Key Vault for encryption keys, required only if external_key_store_id is not set (only used if enable_cmk_encryption is true)"
  default     = null
}

variable "kv_encryption_key_name" {
  type        = string
  description = "Name of Key Vault Encryption Key (only used if enable_cmk_encryption is true)"
  default     = "tre-encryption"
}

variable "kv_mgmt_encryption_key_name" {
  type        = string
  description = "Name of Key Vault Encryption Key for management resources (only used if enable_cmk_encryption is true)"
  default     = "tre-mgmt-encryption"
}
