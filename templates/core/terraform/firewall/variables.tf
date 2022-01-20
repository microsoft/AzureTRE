variable "tre_id" {}
variable "location" {}
variable "resource_group_name" {}
variable "log_analytics_workspace_id" {}
variable "deploy_nexus" {}
variable "deploy_gitea" {}
variable "nexus_allowed_fqdns" {
  type        = string
  description = "comma seperated string of allowed FQDNs for Nexus"
  default     = "*pypi.org"
}
variable "gitea_allowed_fqdns" {
  type        = string
  description = "comma seperated string of allowed FQDNs for Gitea"
  default     = "github.com, www.github.com, api.github.com, git-lfs.github.com, *githubusercontent.com"
}

variable "shared_subnet" {
  type = object({
    id = string
    address_prefixes = list(string)
  })
  description = "The ID of the shared subnet"
}

variable "firewall_subnet" {
  type = object({
    id = string
    address_prefixes = list(string)
  })
  description = "The ID of the firewall subnet"
}

variable "resource_processor_subnet" {
  type = object({
    id = string
    address_prefixes = list(string)
  })
  description = "The ID of the resource_processor subnet"
}

variable "web_app_subnet" {
  type = object({
    id = string
    address_prefixes = list(string)
  })
  description = "The ID of the web app subnet"
}
