locals {
  core_resource_group_name       = "rg-${var.tre_id}"
  workspace_resource_name_suffix = "${var.tre_id}-ws-${var.short_workspace_id}"

  import_approved_sys_topic_name   = "evgt-airlock-import-approved-${local.workspace_resource_name_suffix}"
  export_inprogress_sys_topic_name = "evgt-airlock-export-inprog-${local.workspace_resource_name_suffix}"
  export_rejected_sys_topic_name   = "evgt-airlock-export-rejected-${local.workspace_resource_name_suffix}"
  export_blocked_sys_topic_name    = "evgt-airlock-export-blocked-${local.workspace_resource_name_suffix}"

  blob_created_topic_name                = "airlock-blob-created"
  airlock_malware_scan_result_topic_name = var.airlock_malware_scan_result_topic_name

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

  airlock_blob_data_contributor = [
    azurerm_storage_account.sa_import_approved.id,
    azurerm_storage_account.sa_export_internal.id,
    azurerm_storage_account.sa_export_inprogress.id,
    azurerm_storage_account.sa_export_rejected.id,
    azurerm_storage_account.sa_export_blocked.id
  ]

  api_sa_data_contributor = [
    azurerm_storage_account.sa_import_approved.id,
    azurerm_storage_account.sa_export_internal.id,
    azurerm_storage_account.sa_export_inprogress.id
  ]
}
