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

variable "address_space" {
  type        = string
  description = "VNet address space for the workspace services"
}

variable "deploy_app_service_plan" {
  type        = bool
  default     = true
  description = "Deploy app service plan"
}

variable "app_service_plan_sku" {
  type        = string
  default     = "P1v3"
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
variable "client_id" {
  type        = string
  default     = ""
  description = "The client id of the workspace in the identity provider, this is passed in so that we may return it as an output."
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


locals {
  core_vnet                      = "vnet-${var.tre_id}"
  short_workspace_id             = substr(var.tre_resource_id, -4, -1)
  core_resource_group_name       = "rg-${var.tre_id}"
  workspace_resource_name_suffix = "${var.tre_id}-ws-${local.short_workspace_id}"
  storage_name                   = lower(replace("stg${substr(local.workspace_resource_name_suffix, -8, -1)}", "-", ""))
  keyvault_name                  = lower("kv-${substr(local.workspace_resource_name_suffix, -20, -1)}")
  vnet_subnets                   = cidrsubnets(var.address_space, 1, 1)
  services_subnet_address_prefix = local.vnet_subnets[0]
  webapps_subnet_address_prefix  = local.vnet_subnets[1]
}
