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

  airlock_function_app_name = "func-airlock-processor-${var.tre_id}"
  airlock_function_sa_name  = lower(replace("stairlockp${var.tre_id}", "-", ""))

  servicebus_connection              = "SERVICEBUS_CONNECTION"
  step_result_eventgrid_connection   = "EVENT_GRID_STEP_RESULT_CONNECTION"
  data_deletion_eventgrid_connection = "EVENT_GRID_DATA_DELETION_CONNECTION"
}
