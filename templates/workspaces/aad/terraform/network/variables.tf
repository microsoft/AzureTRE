variable "location" {}
variable "tre_id" {}
variable "address_space" {}
variable "ws_resource_group_name" {}
variable "tre_resource_id" {}
variable "enable_local_debugging" {
  type        = bool
  default     = false
  description = "This will allow keyvault access over the internet. Set to true to allow deploying this from a local machine."
}
