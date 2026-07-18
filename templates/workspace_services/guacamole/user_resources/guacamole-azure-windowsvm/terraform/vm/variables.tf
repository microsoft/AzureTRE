variable "tre_id" {
  type = string
}
variable "workspace_id" {
  type = string
}
variable "parent_service_id" {
  type = string
}
variable "tre_resource_id" {
  type = string
}

variable "image" {
  type = string
}
variable "vm_size" {
  type = string
}
variable "image_gallery_id" {
  type    = string
  default = ""
}
variable "vm_sizes" {
  type        = map(string)
  description = "Map of friendly VM size name to Azure VM SKU, taken from porter.yaml"
}
variable "image_details" {
  type        = any
  description = "Map of image options, taken from porter.yaml"
}

variable "admin_username" {
  type        = string
  description = "The admin username for the VM, computed by the caller"
}
variable "nexus_proxy_url" {
  type        = string
  description = "The Nexus proxy URL used to configure package managers in vm_config.ps1"
}

variable "shared_storage_access" {
  type    = bool
  default = false
}
variable "storage_account_name" {
  type    = string
  default = ""
}
variable "storage_account_key" {
  type      = string
  default   = ""
  sensitive = true
}
variable "storage_account_file_host" {
  type    = string
  default = ""
}
variable "file_share_name" {
  type    = string
  default = ""
}

variable "extra_custom_data" {
  type        = string
  default     = ""
  description = "Optional already-rendered script appended to custom_data after vm_config.ps1 (e.g. the airlock review-data download)"
}

variable "enable_cmk_encryption" {
  type    = bool
  default = false
}
variable "key_store_id" {
  type = string
}

variable "enable_shutdown_schedule" {
  type    = bool
  default = false
}
variable "shutdown_time" {
  type    = string
  default = "00:00"
}
variable "shutdown_timezone" {
  type    = string
  default = "UTC"
}

variable "enable_nic_destroy_wait" {
  type        = bool
  default     = false
  description = "When true, waits before destroying the NIC (used by the airlock review VMs)"
}

variable "extra_tags" {
  type        = map(string)
  default     = {}
  description = "Additional tags merged into the standard user-resource tags"
}
