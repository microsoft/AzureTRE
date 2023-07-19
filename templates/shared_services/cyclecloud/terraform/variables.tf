variable "tre_id" {}
variable "tre_resource_id" {}
variable "arm_environment" {}
variable "tags" {
  type        = map(string)
  description = "Tags to be applied to all resources"
  default = {}
}

