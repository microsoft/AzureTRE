variable "location" {
  type        = string
  description = "Azure region for deployment of core TRE services"
}

variable "workspace_id" {
  type        = string
  description = "ID of the TRE Workspace (e.g. tre-dev-1111)"
}
