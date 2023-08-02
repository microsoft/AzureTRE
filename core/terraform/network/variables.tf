variable "tre_id" {}
variable "location" {}
variable "resource_group_name" {}
variable "core_address_space" {}
variable "arm_environment" {}
variable "tre_core_tags" {
  type        = map(string)
  description = "Tags to be applied to all resources"
  default     = {}
}
