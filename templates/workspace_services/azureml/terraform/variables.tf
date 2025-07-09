variable "workspace_id" {
  type = string
}
variable "tre_id" {
  type = string
}
variable "tre_resource_id" {
  type = string
}
variable "display_name" {
  type = string
}
variable "description" {
  type = string
}
variable "is_exposed_externally" {
  type = bool
}
variable "address_space" {
  type = string
}
variable "arm_tenant_id" {
  type = string
}
variable "auth_tenant_id" {
  type        = string
  description = "Used to authenticate into the AAD Tenant to get app role members"
}
variable "auth_client_id" {
  type        = string
  description = "Used to authenticate into the AAD Tenant to get app role members"
}
variable "auth_client_secret" {
  type        = string
  sensitive   = true
  description = "Used to authenticate into the AAD Tenant to get app role members"
}
variable "arm_environment" {
  type = string
}
variable "azure_environment" {
  type = string
}
variable "enable_cmk_encryption" {
  type    = bool
  default = false
}
variable "key_store_id" {
  type = string
}
variable "log_analytics_workspace_name" {
  type = string
}
