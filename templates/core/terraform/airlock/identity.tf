data "azurerm_cosmosdb_account" "tre-db-account" {
  name                = "cosmos-${var.tre_id}"
  resource_group_name = var.resource_group_name
}

data "azurerm_container_registry" "mgmt_acr" {
  name                = var.mgmt_acr_name
  resource_group_name = var.mgmt_resource_group_name
}

resource "azurerm_user_assigned_identity" "airlock_id" {
  resource_group_name = var.resource_group_name
  location            = var.location
  tags                = local.tre_core_tags

  name = "id-airlock-${var.tre_id}"

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_role_assignment" "acrpull_role" {
  scope                = data.azurerm_container_registry.mgmt_acr.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.airlock_id.principal_id
}

resource "azurerm_role_assignment" "servicebus_sender" {
  scope                = data.azurerm_servicebus_namespace.airlock_sb.id
  role_definition_name = "Azure Service Bus Data Sender"
  principal_id         = azurerm_user_assigned_identity.airlock_id.principal_id
}

resource "azurerm_role_assignment" "servicebus_receiver" {
  scope                = data.azurerm_servicebus_namespace.airlock_sb.id
  role_definition_name = "Azure Service Bus Data Receiver"
  principal_id         = azurerm_user_assigned_identity.airlock_id.principal_id
}

resource "azurerm_role_assignment" "cosmos_contributor" {
  scope                = data.azurerm_cosmosdb_account.tre-db-account.id
  role_definition_name = "Contributor"
  principal_id         = azurerm_user_assigned_identity.airlock_id.principal_id
}

resource "azurerm_role_assignment" "eventgrid_data_sender" {
  scope                = azurerm_eventgrid_topic.status_changed.id
  role_definition_name = "EventGrid Data Sender"
  principal_id         = var.api_principal_id
}
