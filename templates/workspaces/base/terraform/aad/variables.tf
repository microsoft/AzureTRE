variable "key_vault_id" {}
variable "workspace_resource_name_suffix" {}
variable "workspace_owner_object_id" {}
variable "tre_workspace_tags" {}
variable "aad_redirect_uris_b64" {
  type = string # list of objects like [{"name": "my uri 1", "value": "https://..."}, {}]
}
variable "create_aad_groups" {}
