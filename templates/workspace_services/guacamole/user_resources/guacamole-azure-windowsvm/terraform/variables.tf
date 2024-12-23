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
variable "enable_cmk_encryption" {
  type    = bool
  default = false
}
variable "key_store_id" {
  type = string
}
variable "tre_url" {
  type = string
  validation {
    condition     = startswith(var.tre_url, "http") && length(var.tre_url) > 10
    error_message = "Invalid tre_url. Must start with http or https."
  }
}
