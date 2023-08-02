variable "workspace_id" {}
variable "tre_id" {}
variable "parent_service_id" {}
variable "tre_resource_id" {}
variable "image" {}
variable "vm_size" {}
variable "image_gallery_id" {
  default = ""
}
variable "airlock_request_sas_url" {}

variable "tags" {
  type        = map(string)
  description = "Tags to be applied to all resources"
  default     = {}
}
