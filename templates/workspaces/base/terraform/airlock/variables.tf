variable "location" {
  type = string
}
variable "tre_id" {
  type = string
}
variable "ws_resource_group_name" {
  type = string
}
variable "services_subnet_id" {
  type = string
}
variable "short_workspace_id" {
  type = string
}
variable "tre_workspace_tags" {
  type = map(string)
}
variable "arm_environment" {
  type = string
}
variable "workspace_id" {
  type        = string
  description = "The workspace ID used for ABAC conditions on global workspace storage"
}
