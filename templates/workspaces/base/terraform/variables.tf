variable "tre_id" {
  type        = string
  description = "Unique TRE ID"
}

variable "tre_resource_id" {
  type        = string
  description = "Resource ID"
}

variable "workspace_subscription_id" {
  type        = string
  description = "Subscription ID for the workspace resources"
  default     = ""
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

variable "core_api_client_id" {
  type        = string
  description = "The client id of the core API application."
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
variable "enable_backup" {
  type        = bool
  default     = true
  description = "Enable backups for the workspace"
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
variable "ui_client_id" {
  type = string
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

variable "arm_environment" {
  type = string
}

variable "enable_cmk_encryption" {
  type        = bool
  default     = false
  description = "Enable CMK encryption for the workspace"
}

variable "key_store_id" {
  type        = string
  description = "ID of the Key Vault to store CMKs in (only used if enable_cmk_encryption is true)"
}

variable "storage_account_redundancy" {
  type        = string
  default     = "GRS"
  description = "The redundancy option for the storage account in the workspace: GRS (Geo-Redundant Storage) or ZRS (Zone-Redundant Storage)."
}
variable "auto_grant_workspace_consent" {
  type        = bool
  default     = false
  description = "A boolean indicating if the admin consent should be auto granted to the workspace"
}

variable "enable_dns_policy" {
  type        = bool
  description = "Whether, or not, to add a DNS security policy with an allow-list. This is a preview feature that can be enabled to prevent data exfiltration via DNS."
  default     = false
}

variable "enable_airlock_malware_scanning" {
  type        = bool
  default     = false
  description = "Enable Airlock malware scanning for the workspace"
}

variable "airlock_malware_scan_result_topic_name" {
  type        = string
  description = "The name of the topic to publish scan results to"
  default     = null
}
