variable "enabled" {
  type        = bool
  default     = false
  description = "Create a private certificate cache for a CI validation environment."
}

variable "vault_name" {
  type        = string
  description = "Name of the dedicated CI certificate vault."
}

variable "location" {
  type        = string
  description = "Azure region of the CI environment."
}

variable "resource_group_name" {
  type        = string
  description = "Resource group of the CI environment."
}

variable "tenant_id" {
  type        = string
  description = "Tenant that owns the CI environment."
}

variable "resource_processor_principal_id" {
  type        = string
  description = "Resource processor identity allowed to import and restore cached certificates."
}

variable "deployer_principal_id" {
  type        = string
  description = "CI deployer identity allowed to administer the cache vault."
}

variable "shared_subnet_id" {
  type        = string
  description = "Subnet for the private vault endpoint."
}

variable "private_dns_zone_id" {
  type        = string
  description = "Existing private vault DNS zone."
}

variable "log_analytics_workspace_id" {
  type        = string
  description = "Workspace for vault audit events."
}

variable "purge_protection_enabled" {
  type        = bool
  default     = true
  description = "Apply the environment's purge-protection policy to retained certificates."
}

variable "tags" {
  type        = map(string)
  description = "TRE resource tags."
}
