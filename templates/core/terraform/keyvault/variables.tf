variable "tre_id" {}
variable "location" {}
variable "resource_group_name" {}
variable "core_vnet" {}
variable "shared_subnet" {}
variable "tenant_id" {}
variable "deployment_processor_azure_client_id" {}

variable "deployment_processor_azure_client_secret" {
  sensitive   = true
}
