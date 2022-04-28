variable "tre_id" {
  type        = string
  description = "Unique TRE ID"
}

variable "stateful_resources_locked" {
  type        = bool
  default     = true
  description = "Used to add locks on resources with state"
}

variable "api_driven_rule_collections" {
  type = list(object({
    name     = string
    priority = number
    action   = string
    rules = list(object({
      name        = string
      description = string
      protocols = list(object({
        port = string
        type = string
      }))
      target_fqdns     = list(string)
      source_addresses = list(string)
    }))
  }))
  default = []
}
