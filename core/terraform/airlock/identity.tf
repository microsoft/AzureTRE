resource "azurerm_user_assigned_identity" "airlock_id" {
  resource_group_name = var.resource_group_name
  location            = var.location
  name                = "id-airlock-${var.tre_id}"
  tags                = var.tre_core_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_role_assignment" "acrpull_role" {
  scope                = var.acr_id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.airlock_id.principal_id
}

resource "azurerm_role_assignment" "servicebus_sender" {
  scope                = var.airlock_servicebus.id
  role_definition_name = "Azure Service Bus Data Sender"
  principal_id         = azurerm_user_assigned_identity.airlock_id.principal_id
}

resource "azurerm_role_assignment" "servicebus_receiver" {
  scope                = var.airlock_servicebus.id
  role_definition_name = "Azure Service Bus Data Receiver"
  principal_id         = azurerm_user_assigned_identity.airlock_id.principal_id
}

resource "azurerm_role_assignment" "eventgrid_data_sender_status_changed" {
  scope                = azurerm_eventgrid_topic.status_changed.id
  role_definition_name = "EventGrid Data Sender"
  principal_id         = var.api_principal_id
}

resource "azurerm_role_assignment" "eventgrid_data_sender_notification" {
  scope                = azurerm_eventgrid_topic.airlock_notification.id
  role_definition_name = "EventGrid Data Sender"
  principal_id         = var.api_principal_id
}

resource "azurerm_role_assignment" "eventgrid_data_sender_step_result" {
  scope                = azurerm_eventgrid_topic.step_result.id
  role_definition_name = "EventGrid Data Sender"
  principal_id         = azurerm_user_assigned_identity.airlock_id.principal_id
}

resource "azurerm_role_assignment" "eventgrid_data_sender_data_deletion" {
  scope                = azurerm_eventgrid_topic.data_deletion.id
  role_definition_name = "EventGrid Data Sender"
  principal_id         = azurerm_user_assigned_identity.airlock_id.principal_id
}

resource "azurerm_role_assignment" "airlock_blob_data_contributor" {
  count                = length(local.airlock_sa_blob_data_contributor)
  scope                = local.airlock_sa_blob_data_contributor[count.index]
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.airlock_id.principal_id
}

# This might be considered redundent since we give Virtual Machine Contributor
# at the subscription level, but best to be explicit.
resource "azurerm_role_assignment" "api_sa_data_contributor" {
  count                = length(local.api_sa_data_contributor)
  scope                = local.api_sa_data_contributor[count.index]
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = var.api_principal_id
}

# Permissions needed for the Function Host to work correctly.
resource "azurerm_role_assignment" "function_host_storage" {
  for_each             = toset(["Storage Account Contributor", "Storage Blob Data Owner", "Storage Queue Data Contributor"])
  scope                = azurerm_storage_account.sa_airlock_processor_func_app.id
  role_definition_name = each.value
  principal_id         = azurerm_user_assigned_identity.airlock_id.principal_id
}
