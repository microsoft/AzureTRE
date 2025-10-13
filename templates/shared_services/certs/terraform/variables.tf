variable "tre_id" {
  type = string
}

variable "domain_prefix" {
  type = string
}

variable "cert_name" {
  type = string
}

variable "tre_resource_id" {
  type        = string
  description = "Resource ID"
}

variable "enable_cmk_encryption" {
  type    = bool
  default = false
}

variable "key_store_id" {
  type = string
}

variable "arm_environment" {
  type = string
}

variable "enable_auto_renewal" {
  type        = bool
  default     = false
  description = "Enable automatic renewal of the certificate before expiry"
}

variable "renewal_threshold_days" {
  type        = number
  default     = 30
  description = "Number of days before expiry to trigger renewal"
  validation {
    condition     = var.renewal_threshold_days >= 1 && var.renewal_threshold_days <= 60
    error_message = "Renewal threshold must be between 1 and 60 days."
  }
}

variable "renewal_schedule_cron" {
  type        = string
  default     = "0 2 * * 0"
  description = "Cron expression for checking certificate expiry (default: weekly on Sunday at 2 AM)"
}
