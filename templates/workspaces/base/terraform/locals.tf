locals {
  short_workspace_id             = substr(var.tre_resource_id, -4, -1)
  workspace_resource_name_suffix = "${var.tre_id}-ws-${local.short_workspace_id}"
  storage_name                   = lower(replace("stg${substr(local.workspace_resource_name_suffix, -8, -1)}", "-", ""))
  keyvault_name                  = lower("kv-${substr(local.workspace_resource_name_suffix, -20, -1)}")
  redacted_senstive_value        = "REDACTED"
  tre_workspace_tags = {
    tre_id           = var.tre_id
    tre_workspace_id = var.tre_resource_id
  }
  kv_encryption_key_name   = "tre-encryption-${local.workspace_resource_name_suffix}"
  encryption_identity_name = "id-encryption-${var.tre_id}-${local.short_workspace_id}"
  shared_storage_name      = "vm-shared-storage"
}
