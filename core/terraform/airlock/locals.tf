locals {
  version = replace(replace(replace(data.local_file.airlock_processor_version.content, "__version__ = \"", ""), "\"", ""), "\n", "")

  # Consolidated core airlock storage account
  # STorage AirLock consolidated
  airlock_core_storage_name = lower(replace("stalairlock${var.tre_id}", "-", ""))

  # Global Workspace Airlock Storage Account - shared by all workspaces
  # STorage AirLock Global - all workspace stages for all workspaces
  airlock_workspace_global_storage_name = lower(replace("stalairlockg${var.tre_id}", "-", ""))

  # Due to the following issue and Azure not liking delete and immediate recreate under the same name,
  # we had to change the resource names. https://github.com/hashicorp/terraform-provider-azurerm/issues/17389
  topic_name_suffix = "v2-${var.tre_id}"

  step_result_topic_name    = "evgt-airlock-step-result-${local.topic_name_suffix}"
  status_changed_topic_name = "evgt-airlock-status-changed-${local.topic_name_suffix}"
  notification_topic_name   = "evgt-airlock-notification-${local.topic_name_suffix}"
  data_deletion_topic_name  = "evgt-airlock-data-deletion-${local.topic_name_suffix}"
  scan_result_topic_name    = "evgt-airlock-scan-result-${local.topic_name_suffix}"

  step_result_queue_name    = "airlock-step-result"
  status_changed_queue_name = "airlock-status-changed"
  scan_result_queue_name    = "airlock-scan-result"
  data_deletion_queue_name  = "airlock-data-deletion"
  blob_created_topic_name   = "airlock-blob-created"

  blob_created_al_processor_subscription_name = "airlock-blob-created-airlock-processor"

  step_result_eventgrid_subscription_name    = "evgs-airlock-update-status"
  status_changed_eventgrid_subscription_name = "evgs-airlock-status-changed"
  data_deletion_eventgrid_subscription_name  = "evgs-airlock-data-deletion"
  scan_result_eventgrid_subscription_name    = "evgs-airlock-scan-result"

  # Legacy (v1) per-stage storage account names - only used when enable_legacy_airlock = true
  import_external_storage_name    = lower(replace("stalimex${var.tre_id}", "-", ""))
  import_in_progress_storage_name = lower(replace("stalimip${var.tre_id}", "-", ""))
  import_rejected_storage_name    = lower(replace("stalimrej${var.tre_id}", "-", ""))
  import_blocked_storage_name     = lower(replace("stalimblocked${var.tre_id}", "-", ""))
  export_approved_storage_name    = lower(replace("stalexapp${var.tre_id}", "-", ""))

  # Legacy (v1) eventgrid topic/subscription names
  import_inprogress_sys_topic_name = "evgt-airlock-import-in-progress-${local.topic_name_suffix}"
  import_rejected_sys_topic_name   = "evgt-airlock-import-rejected-${local.topic_name_suffix}"
  import_blocked_sys_topic_name    = "evgt-airlock-import-blocked-${local.topic_name_suffix}"
  export_approved_sys_topic_name   = "evgt-airlock-export-approved-${local.topic_name_suffix}"

  import_inprogress_eventgrid_subscription_name = "evgs-airlock-import-in-progress-blob-created"
  import_rejected_eventgrid_subscription_name   = "evgs-airlock-import-rejected-blob-created"
  import_blocked_eventgrid_subscription_name    = "evgs-airlock-import-blocked-blob-created"
  export_approved_eventgrid_subscription_name   = "evgs-airlock-export-approved-blob-created"

  # Legacy (v1) role assignment lists
  airlock_sa_blob_data_contributor = var.enable_legacy_airlock ? [
    azurerm_storage_account.sa_import_external[0].id,
    azurerm_storage_account.sa_import_in_progress[0].id,
    azurerm_storage_account.sa_import_rejected[0].id,
    azurerm_storage_account.sa_export_approved[0].id,
    azurerm_storage_account.sa_import_blocked[0].id
  ] : []

  api_sa_data_contributor = var.enable_legacy_airlock ? [
    azurerm_storage_account.sa_import_external[0].id,
    azurerm_storage_account.sa_import_in_progress[0].id,
    azurerm_storage_account.sa_export_approved[0].id
  ] : []

  airlock_function_app_name = "func-airlock-processor-${var.tre_id}"
  airlock_function_sa_name  = lower(replace("stairlockp${var.tre_id}", "-", ""))

  servicebus_connection              = "SERVICEBUS_CONNECTION"
  step_result_eventgrid_connection   = "EVENT_GRID_STEP_RESULT_CONNECTION"
  data_deletion_eventgrid_connection = "EVENT_GRID_DATA_DELETION_CONNECTION"
}
