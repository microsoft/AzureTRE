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

variable "rp_bundle_values" {
  type = map(string)
}

variable "tre_url" {
  type = string
}
