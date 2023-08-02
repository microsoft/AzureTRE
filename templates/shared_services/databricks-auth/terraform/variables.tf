variable "tre_id" {
  type        = string
  description = "Unique TRE ID"
}

variable "tre_resource_id" {
  type        = string
  description = "Unique TRE Resource ID"
}

variable "arm_environment" {}

variable "tags" {
  type        = map(string)
  description = "Tags to be applied to all resources"
  default     = {}
}
