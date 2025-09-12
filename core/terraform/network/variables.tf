variable "tre_id" {
  type = string
}
variable "location" {
  type = string
}
variable "resource_group_name" {
  type = string
}
variable "core_address_space" {
  type = string
}
variable "arm_environment" {
  type = string
}
variable "route_table_id" {
  type        = string
  description = "The ID of the route table to associate with subnets"
  default     = null
}
