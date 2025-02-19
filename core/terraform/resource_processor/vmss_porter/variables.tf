variable "tre_id" {
  type = string
}
variable "location" {
  type = string
}
variable "acr_id" {
  type = string
}
variable "resource_group_name" {
  type = string
}
variable "core_api_client_id" {
  type = string
}
variable "resource_processor_subnet_id" {
  type = string
}
variable "resource_processor_vmss_porter_image_repository" {
  type = string
}
variable "docker_registry_server" {
  type = string
}
variable "service_bus_namespace_id" {
  type = string
}
variable "service_bus_namespace_fqdn" {
  type = string
}
variable "service_bus_resource_request_queue" {
  type = string
}
variable "service_bus_deployment_status_update_queue" {
  type = string
}
variable "mgmt_storage_account_name" {
  type = string
}
variable "mgmt_resource_group_name" {
  type = string
}
variable "terraform_state_container_name" {
  type = string
}
variable "app_insights_connection_string" {
  type = string
}
variable "key_vault_name" {
  type = string
}
variable "key_vault_url" {
  type = string
}
variable "key_vault_id" {
  type = string
}
variable "resource_processor_number_processes_per_instance" {
  type = string
}
variable "resource_processor_vmss_sku" {
  type = string
}
variable "arm_environment" {
  type = string
}
variable "subscription_id" {
  description = "The subscription id to create the resource processor permission/role. If not supplied will use the TF context."
  type        = string
  default     = ""
}
variable "logging_level" {
  type = string
}
variable "firewall_sku" {
  type = string
}
variable "rp_bundle_values" {
  type = map(string)
}

locals {
  rp_bundle_values_formatted = join("\n      ", [for key in keys(var.rp_bundle_values) : "RP_BUNDLE_${key}=${var.rp_bundle_values[key]}"])
}

variable "enable_cmk_encryption" {
  type        = bool
  description = "A boolean indicating if customer managed keys will be used for encryption of supporting resources"
}

variable "key_store_id" {
  type        = string
  description = "ID of the Key Vault to store CMKs in (only used if enable_cmk_encryption is true)"
}

variable "kv_encryption_key_name" {
  type        = string
  description = "Name of Key Vault Encryption Key (only used if enable_cmk_encryption is true)"
}
