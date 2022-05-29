locals {
  # STorage AirLock EXternal
  import_external_storage_name = lower(replace("stalexim${var.tre_id}", "-", ""))
  # STorage AirLock InProgress IMport
  import_in_progress_storage_name = lower(replace("stalipim${var.tre_id}", "-", ""))
  # STorage AirLock REJected IMport
  import_rejected_storage_name = lower(replace("stalrejim${var.tre_id}", "-", ""))
  # STorage AirLock APProved EXPort
  export_approved_storage_name = lower(replace("stalappexp${var.tre_id}", "-", ""))

  import_inprogress_sys_topic_name = "evgt-airlock-import-in-progress-import-${var.tre_id}"
  import_rejected_sys_topic_name   = "evgt-airlock-import-rejected-${var.tre_id}"
  export_approved_sys_topic_name   = "evgt-airlock-export-approved-${var.tre_id}"

  scan_result_topic_name    = "evgt-airlock-scan-result-${var.tre_id}"
  update_status_topic_name  = "evgt-airlock-update-status-${var.tre_id}"
  status_changed_topic_name = "evgt-airlock-status-changed-${var.tre_id}"

  update_status_queue_name     = "airlock-update-status"
  status_changed_queue_name    = "airlock-status-changed"
  scan_result_queue_name       = "airlock-scan-result"
  import_inprogress_queue_name = "airlock-import-in-progress-blob-created"
  import_rejected_queue_name   = "airlock-import-rejected-blob-created"

  import_approved_queue_name   = "airlock-import-approved-blob-created"
  export_inprogress_queue_name = "airlock-export-inprogress-blob-created"
  export_rejected_queue_name   = "airlock-export-rejected-blob-created"
  export_approved_queue_name   = "airlock-export-approved-blob-created"

  update_status_eventgrid_subscription_name     = "airlock-update-status"
  status_changed_eventgrid_subscription_name    = "airlock-status-changed"
  import_inprogress_eventgrid_subscription_name = "airlock-import-in-progress-blob-created"
  import_rejected_eventgrid_subscription_name   = "airlock-import-rejected-blob-created"
  export_approved_eventgrid_subscription_name   = "airlock-export-approved-blob-created"

}
