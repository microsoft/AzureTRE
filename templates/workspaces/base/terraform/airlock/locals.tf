locals {
  core_resource_group_name       = "rg-${var.tre_id}"
  workspace_resource_name_suffix = "${var.tre_id}-ws-${var.short_workspace_id}"

  # Option B: Global workspace airlock storage account name (in core)
  airlock_workspace_global_storage_name = lower(replace("stalairlockg${var.tre_id}", "-", ""))

  # Consolidated workspace airlock storage account (Option A - per workspace)
  airlock_workspace_storage_name = lower(replace("stalairlockws${substr(local.workspace_resource_name_suffix, -8, -1)}", "-", ""))

  import_approved_sys_topic_name   = "evgt-airlock-import-approved-${local.workspace_resource_name_suffix}"
  export_inprogress_sys_topic_name = "evgt-airlock-export-inprog-${local.workspace_resource_name_suffix}"
  export_rejected_sys_topic_name   = "evgt-airlock-export-rejected-${local.workspace_resource_name_suffix}"
  export_blocked_sys_topic_name    = "evgt-airlock-export-blocked-${local.workspace_resource_name_suffix}"

  blob_created_topic_name                = "airlock-blob-created"
  airlock_malware_scan_result_topic_name = var.airlock_malware_scan_result_topic_name

  # Legacy storage account names (kept for backwards compatibility during migration)
  # STorage AirLock IMport APProved
  import_approved_storage_name = lower(replace("stalimapp${substr(local.workspace_resource_name_suffix, -8, -1)}", "-", ""))
  # STorage AirLock EXport INTernal
  export_internal_storage_name = lower(replace("stalexint${substr(local.workspace_resource_name_suffix, -8, -1)}", "-", ""))
  # STorage AirLock EXport InProgress
  export_inprogress_storage_name = lower(replace("stalexip${substr(local.workspace_resource_name_suffix, -8, -1)}", "-", ""))
  # STorage AirLock EXport REJected
  export_rejected_storage_name = lower(replace("stalexrej${substr(local.workspace_resource_name_suffix, -8, -1)}", "-", ""))
  # STorage AirLock EXport BLOCKED
  export_blocked_storage_name = lower(replace("stalexblocked${substr(local.workspace_resource_name_suffix, -8, -1)}", "-", ""))
}
