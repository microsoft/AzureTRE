variable "workspace_id" {}
variable "tre_id" {}

variable "resource_id" {}

variable "mgmt_acr_name" {}
variable "mgmt_resource_group_name" {}

variable "image_name" {
  type        = string
  description = "value"
  default     = "MLflow/Server"
}
variable "image_tag" {
  type        = string
  description = "value"
  default     = "v1.0"
}

variable "arm_use_msi" {}
variable "arm_tenant_id" {}
variable "arm_client_id" {}
variable "arm_client_secret" {}

variable "mlflow_storage_limit" {
  type        = number
  description = "Space allocated in GB for MLflow data in Azure Files Share"
  default     = 1024
}

variable "is_exposed_externally" {
  type        = bool
  description = "Is the webapp available on the public internet"
  default     = false
}
