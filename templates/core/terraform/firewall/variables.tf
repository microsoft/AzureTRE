variable "tre_id" {}
variable "location" {}
variable "resource_group_name" {}
variable "log_analytics_workspace_id" {}
variable "deploy_nexus" {}
variable "deploy_gitea" {}
variable "nexus_allowed_fqdns" {
  type    = list(string)
  default = ["pypi.org"]
}
variable "gitea_allowed_fqdns" {
  type    = list(string)
  default = ["github.com", "www.github.com"]
}
