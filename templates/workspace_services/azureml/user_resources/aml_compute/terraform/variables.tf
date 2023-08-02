variable "workspace_id" {}
variable "tre_id" {}
variable "vm_size_sku" {

}
variable "tre_resource_id" {}
variable "parent_service_id" {}
variable "auth_tenant_id" {}
variable "user_object_id" {}

variable "tags" {
  type        = map(string)
  description = "Tags to be applied to all resources"
  default     = {}
}
