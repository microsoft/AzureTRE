locals {
  short_workspace_id    = substr(var.tre_resource_id, -4, -1)
  vault_name            = "arsv-${var.tre_id}-ws-${local.short_workspace_id}"
  vm_backup_policy_name = "abp-vm-${var.tre_id}-ws-${local.short_workspace_id}"
  fs_backup_policy_name = "abp-fs-${var.tre_id}-ws-${local.short_workspace_id}"
}
