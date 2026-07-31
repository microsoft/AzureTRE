# Azure Cosmos DB (optional)
# Creates Cosmos DB for agent state persistence and conversation history

resource "azurerm_cosmosdb_account" "agents" {
  count = var.enable_agent_service ? 1 : 0

  name                               = "cosmos-${local.service_resource_name_suffix}-${random_string.suffix.result}"
  location                           = data.azurerm_resource_group.ws.location
  resource_group_name                = data.azurerm_resource_group.ws.name
  offer_type                         = "Standard"
  kind                               = "GlobalDocumentDB"
  automatic_failover_enabled         = false
  public_network_access_enabled      = var.is_exposed_externally
  local_authentication_disabled      = false
  access_key_metadata_writes_enabled = true

  consistency_policy {
    consistency_level = "Session"
  }

  geo_location {
    location          = data.azurerm_resource_group.ws.location
    failover_priority = 0
  }

  # Provisioned account with a total throughput cap. The Foundry Agent Service
  # capability host creates its own "enterprise_memory" database and containers;
  # serverless is not used as the Standard Agent Setup expects provisioned throughput.
  capacity {
    total_throughput_limit = 4000
  }

  tags = local.workspace_service_tags

  timeouts {
    create = "60m"
    update = "60m"
    delete = "30m"
  }

  lifecycle {
    ignore_changes = [tags]
  }
}

# Private endpoint for Cosmos DB
resource "azurerm_private_endpoint" "cosmos_db" {
  count = var.enable_agent_service && !var.is_exposed_externally ? 1 : 0

  name                = "pe-${azurerm_cosmosdb_account.agents[0].name}"
  location            = data.azurerm_resource_group.ws.location
  resource_group_name = data.azurerm_resource_group.ws.name
  subnet_id           = data.azurerm_subnet.services.id
  tags                = local.workspace_service_tags

  private_service_connection {
    name                           = "psc-${azurerm_cosmosdb_account.agents[0].name}"
    private_connection_resource_id = azurerm_cosmosdb_account.agents[0].id
    is_manual_connection           = false
    subresource_names              = ["Sql"]
  }

  private_dns_zone_group {
    name                 = "dns-${azurerm_cosmosdb_account.agents[0].name}"
    private_dns_zone_ids = [data.azurerm_private_dns_zone.cosmos_db[0].id]
  }

  lifecycle {
    ignore_changes = [tags]
  }
}

# Control-plane role assignment for the AI Foundry project (agent) identity
resource "azurerm_role_assignment" "ai_foundry_cosmos_operator" {
  count = var.enable_agent_service ? 1 : 0

  scope                = azurerm_cosmosdb_account.agents[0].id
  role_definition_name = "Cosmos DB Operator"
  principal_id         = azurerm_cognitive_account_project.default.identity[0].principal_id
}

# Data-plane role assignment so the agent identity can read/write threads and
# conversation state in Cosmos DB (SQL API built-in Data Contributor).
resource "azurerm_cosmosdb_sql_role_assignment" "ai_foundry_cosmos_data_contributor" {
  count = var.enable_agent_service ? 1 : 0

  resource_group_name = data.azurerm_resource_group.ws.name
  account_name        = azurerm_cosmosdb_account.agents[0].name
  role_definition_id  = "${azurerm_cosmosdb_account.agents[0].id}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002"
  principal_id        = azurerm_cognitive_account_project.default.identity[0].principal_id
  scope               = azurerm_cosmosdb_account.agents[0].id
}

# Connection from AI Foundry Project to Cosmos DB
# This provides the agent thread storage referenced by the capability host.
resource "azapi_resource" "cosmos_db_connection" {
  count = var.enable_agent_service ? 1 : 0

  type      = "Microsoft.CognitiveServices/accounts/projects/connections@2025-04-01-preview"
  name      = "cosmos-db"
  parent_id = azurerm_cognitive_account_project.default.id

  schema_validation_enabled = false

  body = {
    properties = {
      category = "CosmosDb"
      target   = "https://${azurerm_cosmosdb_account.agents[0].name}.documents.azure.com:443/"
      authType = "AAD"
      metadata = {
        ApiType    = "Azure"
        ResourceId = azurerm_cosmosdb_account.agents[0].id
        location   = data.azurerm_resource_group.ws.location
      }
    }
  }

  depends_on = [
    azurerm_cosmosdb_account.agents,
    azurerm_private_endpoint.cosmos_db,
    azurerm_role_assignment.ai_foundry_cosmos_operator,
    azurerm_cosmosdb_sql_role_assignment.ai_foundry_cosmos_data_contributor,
    azurerm_cognitive_account_project.default
  ]
}
