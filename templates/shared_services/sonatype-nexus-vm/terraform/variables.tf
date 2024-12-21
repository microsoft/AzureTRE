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

variable "vm_size" {
  type        = string
  description = "The size of the VM to be deployed"
  default     = "Standard_B2ms"
}
