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

variable "api_identity_principal_id" {
  type        = string
  description = "Principal (object) id of the core API managed identity, used as the subject of the workspace app registration federated identity credential."
}

