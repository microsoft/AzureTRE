variable "tre_id" {
  type = string
}

variable "domain_prefix" {
  type = string
}

variable "cert_name" {
  type = string
}

variable "tre_resource_id" {
  type        = string
  description = "Resource ID"
}

variable "tags" {
  type        = map(string)
  description = "Tags to be applied to all resources"
  default = {}
}
