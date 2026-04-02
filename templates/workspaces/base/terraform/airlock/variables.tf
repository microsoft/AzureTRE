variable "location" {
  type = string
}
variable "tre_id" {
  type = string
}
variable "ws_resource_group_name" {
  type = string
}
variable "enable_local_debugging" {
  type = bool
}
variable "services_subnet_id" {
  type = string
}
variable "airlock_processor_subnet_id" {
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
variable "enable_cmk_encryption" {
  type = bool
}
variable "encryption_identity_id" {
  type = string
}
variable "encryption_key_versionless_id" {
  type = string
}
variable "enable_airlock_malware_scanning" {
  type = bool
}
variable "airlock_malware_scan_result_topic_name" {
  type = string
}
