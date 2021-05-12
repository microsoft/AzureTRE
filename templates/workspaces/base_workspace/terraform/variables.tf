variable "location" {
  type        = string
  description = "Azure region for deployment of core TRE services"
}

variable "core_id" {
  type        = string
  description = "ID of the TRE Core (e.g. tre-dev-1111)"
}

variable "ws_id" {
  type        = string
  description = "Workspace ID (sequential)"
}

variable "address_space" {
  type        = string
  description = "Workspace services VNET Address Space"
}
