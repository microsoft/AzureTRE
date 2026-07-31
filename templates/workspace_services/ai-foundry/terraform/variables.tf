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
  description = "The TRE resource ID for this workspace service"
}

variable "arm_environment" {
  type        = string
  description = "The ARM environment"
  default     = "public"
}

variable "display_name" {
  type        = string
  description = "Display name for the AI Foundry service"
  default     = "Azure AI Foundry"
}

variable "openai_model" {
  type        = string
  description = "OpenAI model to deploy in format 'model_name | version'"
  default     = "gpt-4o | 2024-05-13"

  validation {
    condition     = length(split("|", var.openai_model)) == 2
    error_message = "openai_model must be in the format 'model_name | version' (exactly one '|' separator)."
  }
}

variable "openai_model_capacity" {
  type        = number
  description = "Capacity for the OpenAI model deployment (in thousands of tokens per minute)"
  default     = 10
}

variable "is_exposed_externally" {
  type        = bool
  description = "Determines if the AI Foundry resources are accessible from outside the workspace network"
  default     = false
}

variable "enable_agent_service" {
  type        = bool
  description = "Enable the Foundry Agent Service (Standard Setup): provisions Cosmos DB, AI Search and a VNet-injected agent subnet with account/project capability hosts. Adds network injection which can take 30-60+ minutes to provision."
  default     = false
}

variable "address_space" {
  type        = string
  description = "Address space for the AI Foundry agent subnet"
}

variable "workspace_owners_group_id" {
  type        = string
  description = "Object ID of the workspace owners AAD group"

  validation {
    condition     = length(trimspace(var.workspace_owners_group_id)) > 0
    error_message = "workspace_owners_group_id must be set (the parent workspace must expose the owners AAD group object ID)."
  }
}

variable "workspace_researchers_group_id" {
  type        = string
  description = "Object ID of the workspace researchers AAD group"

  validation {
    condition     = length(trimspace(var.workspace_researchers_group_id)) > 0
    error_message = "workspace_researchers_group_id must be set (the parent workspace must expose the researchers AAD group object ID)."
  }
}
