variable "tre_id" {
  type        = string
  description = "Unique identifier for the TRE, such as projectx-dev-1234"
  validation {
    condition     = length(var.tre_id) < 12 && lower(var.tre_id) == var.tre_id
    error_message = "The tre_id value must be lowercase and < 12 chars."
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

variable "core_app_service_plan_sku" {
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

variable "resource_processor_number_processes_per_instance" {
  type        = number
  default     = 5
  description = "The number of CPU processes to run the RP on per VM instance"
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
  description = "A client secret used by the API to authenticate with Azure AD for access to Microsoft Graph."
  sensitive   = true
}

variable "application_admin_client_id" {
  type        = string
  description = "The client id (app id) of the registration in Azure AD for creating AAD Applications."
  sensitive   = true
}

variable "application_admin_client_secret" {
  type        = string
  description = "A client secret used by the Resource Processor to authenticate with Azure AD to create AAD Applications."
  sensitive   = true
}

variable "resource_processor_type" {
  default     = "vmss_porter"
  description = "Which resource processor to deploy."
  type        = string
}

variable "resource_processor_vmss_sku" {
  type        = string
  default     = "Standard_B2s"
  description = "The SKU of the resource processor VMSS."
}

variable "stateful_resources_locked" {
  type        = bool
  default     = true
  description = "Used to add locks on resources with state"
}

variable "ci_git_ref" {
  default     = ""
  description = "The git ref used by the ci to deploy this TRE"
  type        = string
}

variable "enable_local_debugging" {
  default     = false
  description = "This will allow Cosmos to be accessible from your local IP address and add some extra role permissions."
  type        = bool
}

# this var is optional and used to avoid assigning a role on every run.
variable "arm_subscription_id" {
  description = "The subscription id to create the resource processor permission/role. If not supplied will use the TF context."
  type        = string
  default     = ""
}

variable "public_deployment_ip_address" {
  description = "Your local IP address if https://ipecho.net/plain is blocked."
  type        = string
  default     = ""
}

# Important note: it is NOT enough to simply enable the malware scanning on. Further, manual, steps are required
# in order to actually set up the scanner. Setting this property to True without supplying a scanner will result
# in airlock requests being stuck in the in-progress stage.
variable "enable_airlock_malware_scanning" {
  type        = bool
  default     = false
  description = "If False, Airlock requests will skip the malware scanning stage"
}

variable "rp_bundle_values" {
  description = "Additional environment values to set on the resource processor that can be supplied to template bundles"
  type        = map(string)
  default     = {}
}
