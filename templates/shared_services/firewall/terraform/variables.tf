variable "tre_id" {
  type        = string
  description = "Unique TRE ID"
}

variable "stateful_resources_locked" {
  type        = bool
  default     = true
  description = "Used to add locks on resources with state"
}

variable "api_driven_rule_collections_b64" {
  type    = string
  default = "W10=" #b64 for []
}
