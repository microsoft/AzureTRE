variable "workspace_id" {}
variable "tre_id" {}
variable "id" {}
variable "mgmt_resource_group_name" {}
variable "hue_storage_limit" {
  type        = number
  description = "Space allocated in GB for the hue data in Azure Files Share"
  default     = 100
}
