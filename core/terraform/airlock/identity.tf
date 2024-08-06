data "azurerm_container_registry" "mgmt_acr" {
  name                = var.mgmt_acr_name
  resource_group_name = var.mgmt_resource_group_name
}

resource "azurerm_user_assigned_identity" "airlock_id" {
  resource_group_name = var.resource_group_name
  location            = var.location
  name                = "id-airlock-${var.tre_id}"
  tags                = var.tre_core_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_role_assignment" "acrpull_role" {
  scope                = data.azurerm_container_registry.mgmt_acr.id
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

resource "azurerm_role_assignment" "eventgrid_data_sender" {
  scope                = azurerm_eventgrid_topic.status_changed.id
  role_definition_name = "EventGrid Data Sender"
  principal_id         = var.api_principal_id
}

resource "azurerm_role_assignment" "eventgrid_data_sender_notification" {
  scope                = azurerm_eventgrid_topic.airlock_notification.id
  role_definition_name = "EventGrid Data Sender"
  principal_id         = var.api_principal_id
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
