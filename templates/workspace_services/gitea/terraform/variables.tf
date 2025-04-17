variable "workspace_id" {
  type = string
}
variable "tre_id" {
  type = string
}
variable "id" {
  type = string
}
variable "mgmt_resource_group_name" {
  type = string
}
variable "mgmt_acr_name" {
  type = string
}
variable "aad_authority_url" {
  type = string
}
variable "gitea_storage_limit" {
  type        = number
  description = "Space allocated in GB for the Gitea data in Azure Files Share"
  default     = 100
}
variable "arm_environment" {
  type = string
}
variable "sql_sku" {
  type = string
}
variable "enable_cmk_encryption" {
  type    = bool
  default = false
}
variable "key_store_id" {
  type = string
}
variable "disable_acr_public_access" {
  type        = bool
  description = "A boolean indicating if ACR public access should be disabled"
  default     = false
}