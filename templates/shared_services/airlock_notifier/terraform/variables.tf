variable "tre_id" {
  type        = string
  description = "Unique TRE ID"
}

variable "tre_resource_id" {
  type        = string
  description = "Resource ID"
}

variable "tre_url" {
  type        = string
  description = "TRE URL"
  default     = ""
}

variable "smtp_server_address" {
  type = string
}

variable "smtp_username" {
  type = string
}

variable "smtp_password" {
  type      = string
  sensitive = true
}

variable "smtp_from_email" {
  type = string
}

variable "smtp_server_port" {
  type = string
}

variable "smtp_server_enable_ssl" {
  type    = bool
  default = false
}
