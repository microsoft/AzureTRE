variable "location" {
  type = string
}
variable "tre_id" {
  type = string
}
variable "address_spaces" {
  type = string
}
variable "ws_resource_group_name" {
  type = string
}
variable "tre_workspace_tags" {
  type = map(string)
}
variable "tre_resource_id" {
  type = string
}
variable "arm_environment" {
  type = string
}
variable "enable_dns_policy" {
  type        = bool
  description = "Whether, or not, to add a DNS security policy with an allow-list. This is a preview feature that can be enabled to prevent data exfiltration via DNS."
  default     = false
}
