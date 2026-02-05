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

variable "enable_ai_search" {
  type        = bool
  description = "Enable Azure AI Search for RAG and knowledge retrieval scenarios"
  default     = false
}

variable "enable_cosmos_db" {
  type        = bool
  description = "Enable Azure Cosmos DB for agent state persistence and conversation history"
  default     = false
}

variable "enable_agent_networking" {
  type        = bool
  description = "Enable VNet injection for Standard Agents. Adds network injections which can take 30-60+ minutes to provision. Deploy without this first, then upgrade to enable."
  default     = false
}

variable "address_space" {
  type        = string
  description = "Address space for the AI Foundry agent subnet"
}

variable "workspace_owners_group_id" {
  type        = string
  description = "Object ID of the workspace owners AAD group"
}

variable "workspace_researchers_group_id" {
  type        = string
  description = "Object ID of the workspace researchers AAD group"
}
