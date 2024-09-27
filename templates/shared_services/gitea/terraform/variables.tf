variable "tre_id" {
  type        = string
  description = "Unique TRE ID"
}

variable "tre_resource_id" {
  type        = string
  description = "Resource ID"
}

variable "gitea_allowed_fqdns" {
  type        = string
  description = "comma seperated string of allowed FQDNs for Gitea"
  default     = "github.com, www.github.com, api.github.com, git-lfs.github.com, *githubusercontent.com"
}

variable "gitea_storage_limit" {
  type        = number
  description = "Space allocated in GB for the Gitea data in Azure Files Share"
  default     = 1024
}

variable "mgmt_resource_group_name" {
  type        = string
  description = "Resource group name for TRE management"
}

variable "acr_name" {
  type        = string
  description = "Name of Azure Container Registry"
}

variable "arm_environment" {
  type = string
}

variable "sql_sku" {
  type = string
}
