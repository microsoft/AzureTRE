variable "workspace_id" {}
variable "tre_id" {}
variable "tre_resource_id" {}
variable "sql_sku" {}
variable "db_name" {}
variable "storage_mb" {
  type = number
  validation {
    condition     = var.storage_mb > 5119 && var.storage_mb < 1048577
    error_message = "The storage value is out of range."
  }
}
variable "arm_environment" {}