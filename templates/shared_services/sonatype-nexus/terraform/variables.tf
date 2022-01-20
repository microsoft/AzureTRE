variable "tre_id" {
  type        = string
  description = "Unique TRE ID"
}

variable "location" {
  type        = string
  description = "Azure location (region) for deployment of core TRE services"
}

variable "storage_account_name" {
  type        = string
  description = "The name of the storage account to use"
}

variable "nexus_storage_limit" {
  type        = number
  description = "Space allocated in GB for the Nexus data in Azure Files Share"
  default     = 1024
}

variable "shared_subnet_id" {
  type        = string
  description = "The ID of the shared subnet in which to create a private endpoint"
}

variable "web_app_subnet_id" {
  type        = string
  description = "The ID of the web app subnet to connect to"
}

variable "private_dns_zone_azurewebsites_id" {
  type = string
  description = "The ID of the private DNS zone to use for the private endpoint"
}

variable "nexus_allowed_fqdns" {
  type        = string
  description = "comma seperated string of allowed FQDNs for Nexus"
  default     = "*pypi.org"
}
