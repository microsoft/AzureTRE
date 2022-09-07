variable "workspace_id" {}
variable "tre_id" {}
variable "tre_resource_id" {}
variable "arm_use_msi" {
  type = bool
}
variable "arm_tenant_id" {}
variable "arm_client_id" {}
variable "arm_client_secret" {}
variable "display_name" {}
variable "description" {}
variable "is_exposed_externally" {
  type = bool
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
  description = "Used to authenticate into the AAD Tenant to get app role members"
}
