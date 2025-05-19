variable "tre_id" {
  type        = string
  description = "Unique TRE ID"
}

variable "backend_collection_b64" {
  type    = string
  default = "W10=" #b64 for []
}

variable "certificate_name" {}