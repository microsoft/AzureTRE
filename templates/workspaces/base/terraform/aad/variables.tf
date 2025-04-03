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
  type = string
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

