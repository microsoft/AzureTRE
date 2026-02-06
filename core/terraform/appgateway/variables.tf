
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
variable "app_gateway_sku" {
  type = string
}
variable "encryption_identity_id" {
  type = string
}
variable "enable_cmk_encryption" {
  type = bool
}
variable "encryption_key_versionless_id" {
  type = string
}
variable "deployer_principal_id" {
  type = string
}
