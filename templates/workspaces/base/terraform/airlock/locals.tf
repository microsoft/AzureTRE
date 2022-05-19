locals {
  core_resource_group_name       = "rg-${var.tre_id}"
  workspace_resource_name_suffix = "${var.tre_id}-ws-${var.short_workspace_id}"

  egst_accepted_import_sys_topic_name   = "egst-accepted-imp-${local.workspace_resource_name_suffix}"
  egst_inprogress_export_sys_topic_name = "egst-inprog-exp-${local.workspace_resource_name_suffix}"
  egst_rejected_export_sys_topic_name   = "egst-rejected-exp-${local.workspace_resource_name_suffix}"

  # STorage AirLock ACCepted IMport
  airlock_accepted_import_storage_name = lower(replace("stalaccim${local.workspace_resource_name_suffix}", "-", ""))
  # STorage AirLock INTernal EXport
  airlock_internal_export_storage_name = lower(replace("stalintex${local.workspace_resource_name_suffix}", "-", ""))
  # STorage AirLock InProgress EXport
  airlock_inprogress_export_storage_name = lower(replace("stalipex${local.workspace_resource_name_suffix}", "-", ""))
  # STorage AirLock REJected EXport
  airlock_rejected_export_storage_name = lower(replace("stalrejex${local.workspace_resource_name_suffix}", "-", ""))
}
