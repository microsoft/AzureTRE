locals {
  workspace_resource_name_suffix = "${var.tre_id}-ws-${local.short_workspace_id}"

  egst_accepted_import_sys_topic_name   = "egst-accepted-imp-${var.workspace_resource_name_suffix}"
  egst_inprogress_export_sys_topic_name = "egst-inprog-exp-${var.workspace_resource_name_suffix}"
  egst_rejected_export_sys_topic_name   = "egst-rejected-exp-${var.workspace_resource_name_suffix}"

  # STorage AirLock ACCepted
  airlock_accepted_import_storage_name = lower(replace("stalacc${var.workspace_resource_name_suffix}", "-", ""))
  # STorage AirLock INTernal EXport
  airlock_internal_export_storage_name = lower(replace("stalintex${var.workspace_resource_name_suffix}", "-", ""))
  # STorage AirLock InProgress EXport
  airlock_inprogress_export_storage_name = lower(replace("stalipex${var.workspace_resource_name_suffix}", "-", ""))
  # STorage AirLock REJected EXport
  airlock_rejected_export_storage_name = lower(replace("stalrejex${var.workspace_resource_name_suffix}", "-", ""))
}
