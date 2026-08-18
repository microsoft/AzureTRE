variable "location" {
  type = string
}
variable "tre_id" {
  type = string
}
variable "ws_resource_group_name" {
  type = string
}
variable "services_subnet_id" {
  type = string
}
variable "workspace_vnet_id" {
  type        = string
  description = "The workspace virtual network ID, linked to a per-workspace private DNS zone so this workspace resolves the shared global airlock storage account to its own private endpoint"
}
variable "short_workspace_id" {
  type = string
}
variable "tre_workspace_tags" {
  type = map(string)
}
variable "arm_environment" {
  type = string
}
variable "workspace_id" {
  type        = string
  description = "The workspace ID used for ABAC conditions on global workspace storage"
}
variable "register_aad_application" {
  type        = bool
  default     = false
  description = "Whether TRE is permitted to create Entra ID objects. When true, a per-workspace airlock SAS signer app registration is created and used to sign user-delegation SAS (enabling per-workspace ABAC isolation). When false, the shared core API identity signs SAS instead."
}
