variable "resource_group_id" {
  type        = string
  description = "Resource ID of the workspace resource group."
}

variable "blocked_resource_types" {
  type        = set(string)
  description = "Exact Azure resource types whose creation and updates are denied."
  default     = []
  nullable    = false

  validation {
    condition = alltrue([
      for resource_type in var.blocked_resource_types :
      can(regex("^[A-Za-z][A-Za-z0-9.]+/[A-Za-z0-9]+(/[A-Za-z0-9]+)*$", resource_type))
    ])
    error_message = "Use exact resource types such as Microsoft.Bing/accounts, without wildcards, resource names or surrounding spaces."
  }
}
