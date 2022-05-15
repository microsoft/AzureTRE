locals {
  # STorage AirLock EXternal
  airlock_external_storage_name = lower(replace("stalex${var.tre_id}", "-", ""))
  # STorage AirLock InProgress IMport
  airlock_in_progress_import_storage_name = lower(replace("stalipim${var.tre_id}", "-", ""))
  # STorage AirLock REJected IMport
  airlock_rejected_import_storage_name = lower(replace("stalrejim${var.tre_id}", "-", ""))

  egst_inprogress_import_sys_topic_name = "egst-in-prog-import-${var.tre_id}"
  egst_rejected_import_sys_topic_name   = "egst-rejected-import-${var.tre_id}"
  egt_scan_result_topic_name            = "egt-scan-res-${var.tre_id}"
  egt_update_status_topic_name          = "egt-update-status-${var.tre_id}"
  egt_status_changed_topic_name         = "egt-status-changed-${var.tre_id}"
}
