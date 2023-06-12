variable "resource_group_name" {
  type = string
}

variable "location" {
  type = string
}

variable "image_identifier" {
  type = string
}

variable "share_name" {
  type = string
}

variable "share_url" {
  type = string
}

variable "storage_account_name" {
  type = string
}

variable "image_gallery_name" {
  type = string
}

variable "image_definition" {
  type = string
}

variable "template_name" {
  type = string
}

variable "offer_name" {
  type = string
}

variable "publisher_name" {
  type = string
}

variable "sku" {
  type = string
}

variable "os_type" {
  type = string
}

variable "description" {
  type = string
}

variable "hyperv_version" {
  type = string
}

variable "image_builder_id" {
  type        = string
  description = "Resource ID of the image builder user assigned identity"
}
