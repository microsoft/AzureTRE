locals {
  core_resource_group_name       = "rg-${var.tre_id}"
  workspace_resource_name_suffix = "${var.tre_id}-ws-${var.short_workspace_id}"

  import_approved_sys_topic_name   = "evgt-airlock-import-approved-${local.workspace_resource_name_suffix}"
  export_inprogress_sys_topic_name = "evgt-airlock-export-inprog-${local.workspace_resource_name_suffix}"
  export_rejected_sys_topic_name   = "evgt-airlock-export-rejected-${local.workspace_resource_name_suffix}"

  # STorage AirLock APProved IMport
  import_approved_storage_name = lower(replace("stalimapp${substr(local.workspace_resource_name_suffix, -8, -1)}", "-", ""))
  # STorage AirLock INTernal EXport
  export_internal_storage_name = lower(replace("stalexint${substr(local.workspace_resource_name_suffix, -8, -1)}", "-", ""))
  # STorage AirLock InProgress EXport
  export_inprogress_storage_name = lower(replace("stalexip${substr(local.workspace_resource_name_suffix, -8, -1)}", "-", ""))
  # STorage AirLock REJected EXport
  export_rejected_storage_name = lower(replace("stalexrej${substr(local.workspace_resource_name_suffix, -8, -1)}", "-", ""))
}
