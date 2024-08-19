variable "workspace_id" {
  type = string
}
variable "tre_id" {
  type = string
}
variable "tre_resource_id" {
  type = string
}

variable "arm_environment" {
  type = string
}

variable "openai_model_name" {
  type = string
  default = "gpt-35-turbo"
}

variable "openai_model_version" {
  type = string
  default = "0301"
}

variable "is_exposed_externally" {
  type = bool
}
