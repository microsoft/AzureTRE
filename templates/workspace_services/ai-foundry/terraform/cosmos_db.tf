# Azure Cosmos DB (optional)
# Creates Cosmos DB for agent state persistence and conversation history

resource "azurerm_cosmosdb_account" "agents" {
  count = var.enable_cosmos_db ? 1 : 0

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

  capabilities {
    name = "EnableServerless"
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
  count = var.enable_cosmos_db && !var.is_exposed_externally ? 1 : 0

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

# Role assignment for AI Foundry to access Cosmos DB
resource "azurerm_role_assignment" "ai_foundry_cosmos_operator" {
  count = var.enable_cosmos_db ? 1 : 0

  scope                = azurerm_cosmosdb_account.agents[0].id
  role_definition_name = "Cosmos DB Operator"
  principal_id         = azurerm_cognitive_account.ai_foundry.identity[0].principal_id
}

resource "azurerm_role_assignment" "ai_foundry_cosmos_contributor" {
  count = var.enable_cosmos_db ? 1 : 0

  scope                = azurerm_cosmosdb_account.agents[0].id
  role_definition_name = "Cosmos DB Account Reader Role"
  principal_id         = azurerm_cognitive_account.ai_foundry.identity[0].principal_id
}

# Connection from AI Foundry Project to Cosmos DB
# This makes Cosmos DB visible for agent state storage in the AI Foundry portal
resource "azapi_resource" "cosmos_db_connection" {
  count = var.enable_cosmos_db ? 1 : 0

  type      = "Microsoft.CognitiveServices/accounts/projects/connections@2025-04-01-preview"
  name      = "cosmos-db"
  parent_id = azurerm_cognitive_account_project.default.id

  schema_validation_enabled = false

  body = {
    properties = {
      category = "CosmosDB"
      target   = azurerm_cosmosdb_account.agents[0].endpoint
      authType = "AAD"
      metadata = {
        ResourceId = azurerm_cosmosdb_account.agents[0].id
        database   = "AgentsDB"
      }
    }
  }

  depends_on = [
    azurerm_cosmosdb_account.agents,
    azurerm_private_endpoint.cosmos_db,
    azurerm_role_assignment.ai_foundry_cosmos_operator,
    azurerm_role_assignment.ai_foundry_cosmos_contributor,
    azurerm_cognitive_account_project.default
  ]
}
