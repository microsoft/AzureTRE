variable "workspace_id" {}
variable "tre_id" {}
variable "tre_resource_id" {}
variable "arm_environment" {}
variable "address_space" {
  type        = string
  description = "Address space for PostgreSQL's subnet"
}

# ATLAS Database
variable "postgres_sku" {
  type        = string
  default     = "B_Standard_B1ms"
  description = "The SKU of the PostgreSQL database"
}

variable "postgres_storage_size_in_mb" {
  type        = number
  default     = 32768
  description = "The storage size of the PostgreSQL database in MB"
}

# Data Source Configuration
variable "configure_data_source" {
  type = bool
}

variable "data_source_config" {
  type    = string
  default = null
}

variable "data_source_daimons" {
  type    = string
  default = null
}
