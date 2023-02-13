variable "tre_id" {
  type        = string
  description = "Unique TRE ID"
}

variable "tre_resource_id" {
  type        = string
  description = "Resource ID"
}

variable "shared_storage_quota" {
  type        = number
  default     = 50
  description = "Quota (in GB) to set for the VM Shared Storage."
}

variable "location" {
  type        = string
  description = "Azure location (region) for deployment of core TRE services"
}

variable "address_spaces" {
  type        = string
  description = "VNet address space (base 64)"
}

variable "deploy_app_service_plan" {
  type        = bool
  default     = true
  description = "Deploy app service plan"
}

variable "app_service_plan_sku" {
  type        = string
  description = "App Service Plan SKU"
}

variable "enable_local_debugging" {
  type        = bool
  default     = false
  description = "This will allow storage account access over the internet. Set to true to allow deploying this from a local machine."
}

variable "register_aad_application" {
  type        = bool
  default     = false
  description = "Create an AAD application automatically for the Workspace."
}

variable "create_aad_groups" {
  type        = bool
  default     = false
  description = "Create AAD groups automatically for the Workspace Application Roles."
}

variable "enable_airlock" {
  type        = bool
  description = "Controls the deployment of Airlock resources in the workspace."
}

variable "aad_redirect_uris_b64" {
  type    = string # B64 encoded list of objects like [{"name": "my uri 1", "value": "https://..."}, {}]
  default = "W10=" #b64 for []
}

variable "auth_tenant_id" {
  type        = string
  description = "Used to authenticate into the AAD Tenant to create the AAD App"
}
variable "auth_client_id" {
  type        = string
  description = "Used to authenticate into the AAD Tenant to create the AAD App"
}
variable "auth_client_secret" {
  type        = string
  description = "Used to authenticate into the AAD Tenant to create the AAD App"
}

# These variables are only passed in if you are not registering an AAD
# application as they need passing back out
variable "app_role_id_workspace_owner" {
  type        = string
  default     = ""
  description = "The id of the application role WorkspaceOwner in the identity provider, this is passed in so that we may return it as an output."
}
variable "app_role_id_workspace_researcher" {
  type        = string
  default     = ""
  description = "The id of the application role WorkspaceResearcher in the identity provider, this is passed in so that we may return it as an output."
}
variable "app_role_id_workspace_airlock_manager" {
  type        = string
  default     = ""
  description = "The id of the application role AirlockManager in the identity provider, this is passed in so that we may return it as an output."
}
variable "client_id" {
  type        = string
  default     = ""
  description = "The client id of the workspace in the identity provider, this is passed in so that we may return it as an output."
}
variable "client_secret" {
  type        = string
  default     = ""
  description = "The client secret of the workspace in the identity provider, this is passed in so that we may return it as an output."
}
variable "sp_id" {
  type        = string
  default     = ""
  description = "The Service Principal in the Identity provider to be able to get claims, this is passed in so that we may return it as an output."
}
variable "scope_id" {
  type        = string
  default     = ""
  description = "The Service Principal Name or Identifier URI, this is passed in so that we may return it as an output."
}
variable "workspace_owner_object_id" {
  type        = string
  default     = ""
  description = "The Object Id of the user that you wish to be the Workspace Owner. E.g. the TEST_AUTOMATION_ACCOUNT."
}
variable "is_legacy_shortened_ws_id" {
  type        = bool
  description = "Is this workspace used the 'older' 4 chars trimmed ws id."
}
variable "arm_use_msi" {
  type = bool
}
variable "arm_tenant_id" {}
variable "arm_client_id" {}
variable "arm_client_secret" {}
