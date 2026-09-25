variable "workspace_subscription_id" {
  type        = string
  description = "Workspace subscription ID. An empty value uses the core subscription."
  default     = ""
}

variable "workspace_id" {
  type        = string
  description = "ID of the parent workspace."
}

variable "tre_id" {
  type        = string
  description = "ID of the Trusted Research Environment (TRE)."
}

variable "tre_resource_id" {
  type        = string
  description = "TRE resource ID for this workspace service."
}

variable "arm_environment" {
  type        = string
  description = "Azure cloud environment name."
  default     = "public"
}

variable "is_exposed_externally" {
  type        = bool
  description = "Allow access from outside the workspace network. Authentication is still required."
  default     = false
}

variable "local_auth_enabled" {
  type        = bool
  description = "Allow API key authentication alongside Microsoft Entra ID."
  default     = false
}

variable "allowed_fqdns" {
  type        = string
  description = "Base64-encoded JSON array of allowed outbound hostnames. The default deny-all.invalid sentinel preserves outbound blocking. An explicit empty list removes the workaround and allowed external image and MCP requests in live tests on 25 September 2026."
  default     = "WyJkZW55LWFsbC5pbnZhbGlkIl0="
  nullable    = false

  validation {
    condition = try(
      startswith(trimspace(base64decode(var.allowed_fqdns)), "[")
      && length(jsondecode(base64decode(var.allowed_fqdns))) <= 1000
      && length(distinct(jsondecode(base64decode(var.allowed_fqdns)))) == length(jsondecode(base64decode(var.allowed_fqdns)))
      && alltrue([
        for fqdn in jsondecode(base64decode(var.allowed_fqdns)) :
        length(fqdn) <= 253 && can(regex("^([A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?\\.)+[A-Za-z]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?$", fqdn))
      ]),
      false
    )
    error_message = "allowed_fqdns must be a base64-encoded JSON array of up to 1000 unique hostnames, each at most 253 characters. Use exact hostnames, not URLs, wildcards or blank entries. An explicit empty array (W10=) removes the deny-all workaround."
  }
}

variable "openai_model" {
  type        = string
  description = "OpenAI model in the format 'model_name | version'."
  default     = "gpt-5.1 | 2025-11-13"

  validation {
    condition     = var.openai_model == "gpt-5.1 | 2025-11-13"
    error_message = "Select the approved GPT-5.1 model version from this template."
  }
}

variable "openai_model_capacity" {
  type        = number
  description = "A token is a small unit of text that a model processes. Set capacity in thousands of tokens per minute."
  default     = 10

  validation {
    condition     = var.openai_model_capacity >= 1 && var.openai_model_capacity <= 100 && floor(var.openai_model_capacity) == var.openai_model_capacity
    error_message = "Model capacity must be a whole number from 1 to 100."
  }
}

# The parent workspace supplies both group object IDs during deployment. A
# workspace with auth_type Manual creates no Microsoft Entra ID application or
# groups. It therefore supplies an empty string. roles.tf checks this value
# before it creates each assignment. Do not use a variable validation block. Terraform
# also runs variable validation during deletion, which would block deletion
# after a failed deployment.
variable "workspace_owners_group_id" {
  type        = string
  description = "Microsoft Entra ID group object ID for workspace owners. The value is empty if the parent workspace uses auth_type Manual."
}

variable "workspace_researchers_group_id" {
  type        = string
  description = "Microsoft Entra ID group object ID for workspace researchers. The value is empty if the parent workspace uses auth_type Manual."
}
