variable "workspace_id" {
  type        = string
  description = "The workspace ID"
}

variable "tre_id" {
  type        = string
  description = "The TRE ID"
}

variable "tre_resource_id" {
  type        = string
  description = "The workspace service ID"
}

variable "display_name" {
  type        = string
  description = "The workspace service display name"
  default     = "Azure Virtual Desktop"
}

variable "workspace_display_name" {
  type        = string
  description = "The parent TRE workspace display name"
  default     = ""
}

variable "arm_environment" {
  type        = string
  description = "The ARM cloud environment"
}

variable "workspace_subscription_id" {
  type        = string
  description = "The id of the Azure subscription the workspace is deployed to"
  default     = ""
}

variable "auth_client_id" {
  type        = string
  description = "Client ID used for AVD service-principal lookup and optional SSO pre-consent"
}

variable "auth_client_secret" {
  type        = string
  description = "Client secret used for AVD service-principal lookup and optional SSO pre-consent"
  sensitive   = true
}

variable "auth_tenant_id" {
  type        = string
  description = "Tenant containing the workspace application"
}

variable "azure_environment" {
  type        = string
  description = "Azure CLI cloud name"
  default     = "AzureCloud"
}

variable "enable_sso_preconsent" {
  type        = bool
  description = "Create and register a dynamic device group for AVD SSO pre-consent"
  default     = false
}

variable "host_pool_type" {
  type        = string
  description = "The AVD host pool type"
  default     = "Personal"

  validation {
    condition     = contains(["Personal", "Pooled"], var.host_pool_type)
    error_message = "host_pool_type must be Personal or Pooled."
  }
}

variable "workspace_owners_group_id" {
  type        = string
  description = "Object ID of the workspace owners security group"

  validation {
    condition     = can(regex("^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$", var.workspace_owners_group_id))
    error_message = "AVD requires a workspace owners group ID. Enable TRE auto_workspace_group_creation and provision the workspace groups first."
  }
}

variable "workspace_researchers_group_id" {
  type        = string
  description = "Object ID of the workspace researchers security group"

  validation {
    condition     = can(regex("^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$", var.workspace_researchers_group_id))
    error_message = "AVD requires a workspace researchers group ID. Enable TRE auto_workspace_group_creation and provision the workspace groups first."
  }
}

variable "maximum_sessions" {
  type        = number
  description = "Maximum concurrent sessions per pooled host"
  default     = 10

  validation {
    condition     = var.maximum_sessions >= 1 && var.maximum_sessions <= 50
    error_message = "maximum_sessions must be between 1 and 50."
  }
}

variable "pooled_session_host_count" {
  type        = number
  description = "Number of pooled multi-user session hosts"
  default     = 1

  validation {
    condition     = var.pooled_session_host_count >= 1 && var.pooled_session_host_count <= 10 && floor(var.pooled_session_host_count) == var.pooled_session_host_count
    error_message = "pooled_session_host_count must be a whole number between 1 and 10."
  }
}

variable "pooled_vm_size" {
  type        = string
  description = "Virtual machine size for pooled session hosts"
  default     = "Standard_D4s_v6"

  validation {
    condition     = contains(["Standard_D2s_v6", "Standard_D4s_v6", "Standard_D8s_v6", "Standard_D16s_v6"], var.pooled_vm_size)
    error_message = "pooled_vm_size must be one of the supported Dsv6 sizes."
  }
}

variable "enable_clipboard" {
  type        = bool
  description = "Enable clipboard redirection between session and client"
  default     = false
}

variable "clipboard_transfer_direction" {
  type        = string
  description = "Direction of allowed clipboard transfers (disabled, client_to_session, session_to_client, both)"
  default     = "disabled"

  validation {
    condition     = contains(["disabled", "client_to_session", "session_to_client", "both"], var.clipboard_transfer_direction)
    error_message = "clipboard_transfer_direction must be disabled, client_to_session, session_to_client, or both."
  }
}
