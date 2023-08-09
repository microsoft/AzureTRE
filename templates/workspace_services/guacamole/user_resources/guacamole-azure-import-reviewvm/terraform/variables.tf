variable "workspace_id" {
  type        = string
}
variable "tre_id" {
  type        = string
}
variable "parent_service_id" {
  type        = string
}
variable "tre_resource_id" {
  type        = string
}
variable "image" {
  type        = string
}
variable "vm_size" {
  type        = number
}
variable "image_gallery_id" {
  type        = string
  default = ""
}
variable "airlock_request_sas_url" {
  type        = string
}
