locals {
  # STorage AirLock EXternal
  import_external_storage_name = lower(replace("stalimex${var.tre_id}", "-", ""))
  # STorage AirLock InProgress IMport
  import_in_progress_storage_name = lower(replace("stalimip${var.tre_id}", "-", ""))
  # STorage AirLock REJected IMport
  import_rejected_storage_name = lower(replace("stalimrej${var.tre_id}", "-", ""))
  # STorage AirLock APProved EXPort
  export_approved_storage_name = lower(replace("stalexapp${var.tre_id}", "-", ""))

  # Due to the following issue and Azure not liking delete and immediate recreate under the same name,
  # we had to change the resource names. https://github.com/hashicorp/terraform-provider-azurerm/issues/17389
  topic_name_suffix = "v2-${var.tre_id}"

  import_inprogress_sys_topic_name = "evgt-airlock-import-in-progress-${local.topic_name_suffix}"
  import_rejected_sys_topic_name   = "evgt-airlock-import-rejected-${local.topic_name_suffix}"
  export_approved_sys_topic_name   = "evgt-airlock-export-approved-${local.topic_name_suffix}"

  scan_result_topic_name    = "evgt-airlock-scan-result-${local.topic_name_suffix}"
  step_result_topic_name    = "evgt-airlock-step-result-${local.topic_name_suffix}"
  status_changed_topic_name = "evgt-airlock-status-changed-${local.topic_name_suffix}"

  step_result_queue_name    = "airlock-step-result"
  status_changed_queue_name = "airlock-status-changed"
  scan_result_queue_name    = "airlock-scan-result"
  blob_created_topic_name   = "airlock-blob-created"

  blob_created_malware_subscription_name      = "airlock-blob-created-malware-scanner"
  blob_created_al_processor_subscription_name = "airlock-blob-created-airlock-processor"

  step_result_eventgrid_subscription_name       = "evgs-airlock-update-status"
  status_changed_eventgrid_subscription_name    = "evgs-airlock-status-changed"
  import_inprogress_eventgrid_subscription_name = "evgs-airlock-import-in-progress-blob-created"
  import_rejected_eventgrid_subscription_name   = "evgs-airlock-import-rejected-blob-created"
  export_approved_eventgrid_subscription_name   = "evgs-airlock-export-approved-blob-created"

  airlock_function_app_name = "func-airlock-processor-${var.tre_id}"
  airlock_function_sa_name  = "saairlockp${var.tre_id}"
}
