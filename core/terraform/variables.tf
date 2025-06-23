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
  validation {
    condition     = parseint(element(split("/", var.core_address_space), 1), 10) > 0 && parseint(element(split("/", var.core_address_space), 1), 10) <= 22
    error_message = "core_address_space size should be /22 or larger"
  }
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

variable "enable_swagger" {
  type        = bool
  default     = false
  description = "Determines whether the Swagger interface for the API will be available."
  sensitive   = false
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

variable "arm_environment" {
  type        = string
  default     = "public"
  description = "Used as an environment variable in the VMSS to set the Azure cloud for Terraform"
}

variable "arm_use_msi" {
  type        = bool
  default     = false
  description = "Used as an environment variable to determine if Terraform should use a managed identity"
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

variable "enable_airlock_malware_scanning" {
  type        = bool
  default     = false
  description = "If False, Airlock requests will skip the malware scanning stage"
}

variable "enable_airlock_email_check" {
  type        = bool
  default     = false
  description = "If True, prior to airlock requests creation will check users have email addresses"
}

variable "firewall_sku" {
  description = "Azure Firewall SKU"
  type        = string
  default     = ""
}

variable "firewall_force_tunnel_ip" {
  type    = string
  default = ""
}

variable "app_gateway_sku" {
  description = "Application Gateway SKU"
  type        = string
  default     = ""

  validation {
    condition     = contains(["", "Standard_v2", "WAF_v2"], var.app_gateway_sku)
    error_message = "Invalid app_gateway_sku value"
  }
}

variable "rp_bundle_values" {
  description = "Additional environment values to set on the resource processor that can be supplied to template bundles"
  type        = map(string)
  default     = {}
}

variable "is_cosmos_defined_throughput" {
  type    = bool
  default = false
}

variable "kv_purge_protection_enabled" {
  type        = bool
  description = "A boolean indicating if the purge protection will be enabled on the core keyvault."
  default     = true
}

variable "logging_level" {
  type        = string
  default     = "INFO"
  description = "The logging level for the API and Resource Processor"
  validation {
    condition     = contains(["INFO", "DEBUG", "WARNING", "ERROR"], var.logging_level)
    error_message = "logging_level must be one of ERROR, WARNING, INFO, DEBUG"
  }
}

variable "enable_cmk_encryption" {
  type        = bool
  description = "A boolean indicating if customer managed keys will be used for encryption of supporting resources"
  default     = false

  validation {
    condition = var.enable_cmk_encryption == false || (var.enable_cmk_encryption == true && (
      (try(length(var.external_key_store_id), 0) > 0 && try(length(var.encryption_kv_name), 0) == 0) ||
      (try(length(var.external_key_store_id), 0) == 0 && try(length(var.encryption_kv_name), 0) > 0)
    ))
    error_message = "Exactly one of 'external_key_store_id' or 'encryption_kv_name' must be non-empty when enable_cmk_encryption is true."
  }
}

variable "external_key_store_id" {
  type        = string
  description = "ID of external Key Vault to store CMKs in (only required if enable_cmk_encryption is true)"
  default     = ""
}

variable "encryption_kv_name" {
  type        = string
  description = "Name of Key Vault for encryption keys, required only if external_key_store_id is not set (only used if enable_cmk_encryption is true)"
  default     = ""
}

variable "enable_dns_policy" {
  type        = bool
  description = "Whether, or not, to add a DNS security policy with an allow-list. This is a preview feature that can be enabled to prevent data exfiltration via DNS."
  default     = false
}

variable "allowed_dns" {
  type        = list(string)
  description = "When DNS security policy is enabled this list of domains will be added to the allow list."
  default     = []
}

variable "auto_grant_workspace_consent" {
  type        = bool
  description = "A boolean indicating if admin consent should be auto granted to the workspace"
  default     = false
}

variable "user_management_enabled" {
  type        = bool
  description = "Is the Entra ID user management feature enabled (requires a workspace with Entra ID groups enabled, default to false)?"
  default     = false
}

variable "deploy_bastion" {
  type        = bool
  description = "Deploy Azure Bastion"
  default     = true
}

variable "bastion_sku" {
  type        = string
  description = "Azure Bastion SKU"
  default     = "Basic"
  validation {
    condition     = contains(["Developer", "Basic", "Standard", "Premium"], var.bastion_sku)
    error_message = "Invalid bastion_sku value"
  }
}

variable "private_agent_subnet_id" {
  description = "Subnet ID of the github runners"
  type        = string
  default     = ""
}
