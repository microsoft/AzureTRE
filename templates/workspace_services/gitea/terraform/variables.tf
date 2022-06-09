variable "workspace_id" {}
variable "tre_id" {}
variable "id" {}
variable "parent_service_id" {}
variable "mgmt_resource_group_name" {}
variable "mgmt_acr_name" {}
variable "gitea_storage_limit" {
  type        = number
  description = "Space allocated in GB for the Gitea data in Azure Files Share"
  default     = 100
}
variable "openid_client_id" {}
variable "openid_client_secret" {}
variable "openid_authority" {}
