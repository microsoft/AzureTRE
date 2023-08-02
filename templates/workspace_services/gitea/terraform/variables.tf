variable "workspace_id" {}
variable "tre_id" {}
variable "id" {}
variable "mgmt_resource_group_name" {}
variable "mgmt_acr_name" {}
variable "aad_authority_url" {}
variable "gitea_storage_limit" {
  type        = number
  description = "Space allocated in GB for the Gitea data in Azure Files Share"
  default     = 100
}
variable "arm_environment" {}

variable "tags" {
  type        = map(string)
  description = "Tags to be applied to all resources"
  default     = {}
}
