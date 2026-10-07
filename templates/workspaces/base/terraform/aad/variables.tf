variable "key_vault_id" {
  type = string
}
variable "workspace_resource_name_suffix" {
  type = string
}
variable "workspace_owner_object_id" {
  type = string
}
variable "tre_workspace_tags" {
  type = map(string)
}
variable "aad_redirect_uris_b64" {
  type = string # list of objects like [{"name": "my uri 1", "value": "https://..."}, {}]
}
variable "create_aad_groups" {
  type = bool
}
variable "ui_client_id" {
  type = string
}
variable "auto_grant_workspace_consent" {
  type    = bool
  default = false
}
variable "core_api_client_id" {
  type = string
}
variable "existing_identifier_uri" {
  type    = string
  default = ""
}

variable "workspace_password_rotation_days" {
  type        = number
  default     = 365
  description = "Number of days after which the workspace application password is rotated on the next workspace upgrade. The password remains valid for the same period again after rotation."
}
