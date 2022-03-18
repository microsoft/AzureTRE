variable "tre_id" {}
variable "stateful_resources_locked" {
  type        = bool
  default     = true
  description = "Used to add locks on resources with state"
}
