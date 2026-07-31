# Foundry Agent Service (Standard Setup)
#
# When enabled, the AI Foundry account is VNet-injected (see network_injection in
# ai_foundry.tf and the agent subnet in network.tf) and a project-level capability
# host wires together the bring-your-own resources:
#   - thread storage  -> Cosmos DB       (cosmos_db.tf)
#   - vector store     -> Azure AI Search (ai_search.tf)
#   - file storage     -> workspace storage connection (ai_foundry.tf)
#
# With VNet injection configured on the account, only the project-level capability
# host is required (no separate account-level capability host).

# Allow the connections and their role assignments to propagate before the
# capability host is created, otherwise provisioning intermittently fails.
resource "time_sleep" "wait_rbac_before_capability_host" {
  count           = var.enable_agent_service ? 1 : 0
  create_duration = "120s"

  triggers = {
    storage_connection = azapi_resource.storage_connection.id
    search_connection  = azapi_resource.ai_search_connection[0].id
    cosmos_connection  = azapi_resource.cosmos_db_connection[0].id
  }

  depends_on = [
    azapi_resource.storage_connection,
    azapi_resource.ai_search_connection,
    azapi_resource.cosmos_db_connection,
    azurerm_role_assignment.ai_foundry_search_contributor,
    azurerm_role_assignment.ai_foundry_search_index_contributor,
    azurerm_role_assignment.ai_foundry_cosmos_operator,
    azurerm_cosmosdb_sql_role_assignment.ai_foundry_cosmos_data_contributor,
    azurerm_role_assignment.project_storage_blob_contributor
  ]
}

# Project-level agent capability host binding the BYO resources to the agent runtime.
resource "azapi_resource" "agent_capability_host" {
  count = var.enable_agent_service ? 1 : 0

  type      = "Microsoft.CognitiveServices/accounts/projects/capabilityHosts@2025-04-01-preview"
  name      = "agenthost-${local.short_service_id}"
  parent_id = azurerm_cognitive_account_project.default.id

  schema_validation_enabled = false

  body = {
    properties = {
      capabilityHostKind       = "Agents"
      threadStorageConnections = [azapi_resource.cosmos_db_connection[0].name]
      vectorStoreConnections   = [azapi_resource.ai_search_connection[0].name]
      storageConnections       = [azapi_resource.storage_connection.name]
    }
  }

  depends_on = [
    time_sleep.wait_rbac_before_capability_host
  ]

  timeouts {
    create = "60m"
    update = "60m"
    delete = "60m"
    read   = "5m"
  }
}
