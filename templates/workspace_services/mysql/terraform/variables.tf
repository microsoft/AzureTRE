variable "workspace_id" {
  type = string
}
variable "tre_id" {
  type = string
}
variable "tre_resource_id" {
  type = string
}
variable "sql_sku" {
  type = string
}
variable "db_name" {
  type = string
}
variable "storage_mb" {
  type = number
  validation {
    condition     = var.storage_mb > 20479 && var.storage_mb < 16777217
    error_message = "The storage value is out of range."
  }
}
variable "arm_environment" {
  type = string
}
