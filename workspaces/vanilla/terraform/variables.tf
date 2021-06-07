variable "tre_id" {
  type        = string
  description = "Unique TRE ID"
}

variable "workspace_id" {
  type        = string
  description = "Unique 4-character long, alphanumeric workspace ID"
}

variable "location" {
  type        = string
  description = "Azure location (region) for deployment of core TRE services"
}

variable "address_space" {
  type        = string
  description = "VNet address space for the workspace services"
}
