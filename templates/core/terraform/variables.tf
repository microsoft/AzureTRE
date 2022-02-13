variable "tre_id" {
  type        = string
  description = "Unique identifier for the TRE, such as projectx-dev-1234"
  validation {
    condition     = length(var.tre_id) < 12
    error_message = "The tre_id value must be < 12 chars."
  }
}

variable "location" {
  type        = string
  description = "Azure region for deployment of core TRE services"
}

variable "acr_name" {
  type        = string
  description = "Management ACR name"
}

variable "core_address_space" {
  type        = string
  description = "Core services VNET Address Space"
}

variable "tre_address_space" {
  type        = string
  description = "Overall TRE Address Space pool, will be used for workspace VNETs, can be a supernet of address_space."
}

variable "api_image_repository" {
  type        = string
  description = "Repository for API image"
  default     = "microsoft/azuretre/api"
}

variable "api_app_service_plan_sku_tier" {
  type    = string
  default = "PremiumV3"
}

variable "api_app_service_plan_sku_size" {
  type    = string
  default = "P1v3"
}

variable "resource_processor_vmss_porter_image_repository" {
  type        = string
  description = "Repository for resource processor vmms porter image"
  default     = "microsoft/azuretre/resource-processor-vm-porter"
}

variable "mgmt_storage_account_name" {
  type        = string
  description = "Storage account created by bootstrap to hold all Terraform state"
}

variable "mgmt_resource_group_name" {
  type        = string
  description = "Shared management resource group"
}

variable "terraform_state_container_name" {
  type        = string
  description = "Name of the storage container for Terraform state"
}

variable "resource_processor_client_id" {
  type        = string
  default     = ""
  description = "The client (app) ID of a service principal with Owner role to the subscription."
}

variable "resource_processor_client_secret" {
  type        = string
  default     = ""
  description = "The client secret (app password) of a service principal with Owner role to the subscription."
}

variable "docker_registry_server" {
  type        = string
  description = "Docker registry server"
}

variable "swagger_ui_client_id" {
  type        = string
  description = "The client id (app id) of the registration in Azure AD for the Swagger UI"
  sensitive   = true
}

variable "aad_tenant_id" {
  type        = string
  description = "The tenant id of the Azure AD used for authentication."
  sensitive   = true
}

variable "api_client_id" {
  type        = string
  description = "The client id (app id) of the registration in Azure AD for the API."
  sensitive   = true
}

variable "api_client_secret" {
  type        = string
  description = "A client secret use by the API to authenticate with Azure AD for access to Microsoft Graph."
  sensitive   = true
}

variable "deploy_gitea" {
  type        = bool
  default     = true
  description = "Deploy the Gitea shared service"
}

variable "deploy_nexus" {
  type        = bool
  default     = true
  description = "Deploy the Nexus shared service"
}

variable "resource_processor_type" {
  default     = "vmss_porter"
  description = "Which resource processor to deploy."
  type        = string
}

variable "debug" {
  type        = bool
  default     = false
  description = "Used to turn debug on within Azure Resources"
}

variable "ci_git_ref" {
  default     = ""
  description = "The git ref used by the ci to deploy this TRE"
  type        = string
}

# this var is optional and used to avoid assigning a role on every run.
variable "arm_subscription_id" {
  description = "The subscription id to create the resource processor permission/role. If not supplied will use the TF context."
  type        = string
  default     = ""
}
