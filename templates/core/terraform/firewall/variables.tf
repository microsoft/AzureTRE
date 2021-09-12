variable "tre_id" {}
variable "location" {}
variable "resource_group_name" {}
variable "log_analytics_workspace_id" {}
variable "deploy_nexus" {}
variable "deploy_gitea" {}
variable "nexus_allowed_fqdns" {
  type        = string
  description = "comma seperated string of allowed FQDNs for Nexus"
  default     = "pypi.org"
}
variable "gitea_allowed_fqdns" {
  type        = string
  description = "comma seperated string of allowed FQDNs for Gitea"
  default     = "github.com, www.github.com"
}
