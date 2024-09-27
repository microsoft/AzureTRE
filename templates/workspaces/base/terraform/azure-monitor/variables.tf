variable "tre_id" {
  type = string
}
variable "location" {
  type = string
}
variable "resource_group_name" {
  type = string
}
variable "resource_group_id" {
  type = string
}
variable "tre_workspace_tags" {
  type = map(string)
}
variable "workspace_subnet_id" {
  type = string
}
variable "azure_monitor_dns_zone_id" {
  type = string
}
variable "azure_monitor_oms_opinsights_dns_zone_id" {
  type = string
}
variable "azure_monitor_ods_opinsights_dns_zone_id" {
  type = string
}
variable "azure_monitor_agentsvc_dns_zone_id" {
  type = string
}
variable "blob_core_dns_zone_id" {
  type = string
}
variable "tre_resource_id" {
  type = string
}
variable "enable_local_debugging" {
  type = bool
}
