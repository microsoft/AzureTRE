variable "tre_id" {
  type = string
}

variable "tre_resource_id" {
  type        = string
  description = "Resource ID"
}

variable "ssl_cert_name" {
  type = string
}

variable "tags" {
  type        = map(string)
  description = "Tags to be applied to all resources"
  default = {}
}
