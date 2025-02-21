variable "workspace_id" {
  type = string
}
variable "tre_id" {
  type = string
}
variable "parent_service_id" {
  type = string
}
variable "tre_resource_id" {
  type = string
}
variable "image" {
  type = string
}
variable "vm_size" {
  type = string
}
variable "shared_storage_access" {
  type = bool
}
variable "shared_storage_name" {
  type = string
}
variable "image_gallery_id" {
  type    = string
  default = ""
}
variable "owner_id" {
  type = string
}
variable "enable_shutdown_schedule" {
  type    = bool
  default = false
}
variable "shutdown_time" {
  type = string
}
variable "shutdown_timezone" {
  type    = string
  default = "UTC"
}
variable "enable_cmk_encryption" {
  type    = bool
  default = false
}
variable "key_store_id" {
  type = string
}
variable "auth_tenant_id" {
  type        = string
  description = "Used to authenticate into the AAD Tenant to create the AAD App"
}
variable "auth_client_id" {
  type        = string
  description = "Used to authenticate into the AAD Tenant to create the AAD App"
}
variable "auth_client_secret" {
  type        = string
  description = "Used to authenticate into the AAD Tenant to create the AAD App"
}
