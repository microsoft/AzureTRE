locals {
  core_resource_group_name       = "rg-${var.tre_id}"
  workspace_resource_name_suffix = "${var.tre_id}-ws-${var.short_workspace_id}"

  # Global workspace airlock storage account name (in core) - shared by all workspaces
  airlock_workspace_global_storage_name = lower(replace("stalairlockg${var.tre_id}", "-", ""))

  blob_created_topic_name                = "airlock-blob-created"
  airlock_malware_scan_result_topic_name = var.airlock_malware_scan_result_topic_name
}
