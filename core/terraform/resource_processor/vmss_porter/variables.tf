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
variable "blob_core_dns_zone_id" {
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
variable "rp_bundle_values" {
  type = map(string)
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

variable "ui_client_id" {
  type        = string
  description = "The client id of the UI application"
}

variable "auto_grant_workspace_consent" {
  type        = bool
  description = "A boolean indicating if admin consent should be auto granted to the workspace"
  default     = false
}

variable "enable_airlock_malware_scanning" {
  type        = bool
  description = "If False, Airlock requests will skip the malware scanning stage"
}

variable "airlock_malware_scan_result_topic_name" {
  type        = string
  description = "Name of the topic to publish Airlock malware scan results to"
}

variable "mgmt_storage_account_id" {
  type        = string
  description = "ID of the management storage account"
}

variable "firewall_policy_id" {
  type        = string
  description = "ID of the firewall policy to use for the resource processor"
}
