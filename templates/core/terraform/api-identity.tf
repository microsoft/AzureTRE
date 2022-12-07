resource "azurerm_user_assigned_identity" "id" {
  resource_group_name = azurerm_resource_group.core.name
  location            = azurerm_resource_group.core.location
  tags                = local.tre_core_tags

  name = "id-api-${var.tre_id}"

  lifecycle { ignore_changes = [tags] }
}

# Needed to include untagged resources in cost reporting #2933
resource "azurerm_role_assignment" "resource_group_reader" {
  scope                = azurerm_resource_group.core.id
  role_definition_name = "Reader"
  principal_id         = azurerm_user_assigned_identity.id.principal_id
}

resource "azurerm_role_assignment" "billing_reader" {
  scope                = data.azurerm_subscription.current.id
  role_definition_name = "Billing Reader"
  principal_id         = azurerm_user_assigned_identity.id.principal_id
}

resource "azurerm_role_assignment" "acrpull_role" {
  scope                = data.azurerm_container_registry.mgmt_acr.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.id.principal_id
}

resource "azurerm_role_assignment" "servicebus_sender" {
  scope                = azurerm_servicebus_namespace.sb.id
  role_definition_name = "Azure Service Bus Data Sender"
  principal_id         = azurerm_user_assigned_identity.id.principal_id
}

resource "azurerm_role_assignment" "servicebus_receiver" {
  scope                = azurerm_servicebus_namespace.sb.id
  role_definition_name = "Azure Service Bus Data Receiver"
  principal_id         = azurerm_user_assigned_identity.id.principal_id
}

resource "azurerm_role_assignment" "cosmos_contributor" {
  scope                = azurerm_cosmosdb_account.tre_db_account.id
  role_definition_name = "Contributor"
  principal_id         = azurerm_user_assigned_identity.id.principal_id
}

