# Azure AI Search (optional)
# Creates Azure Cognitive Search service for RAG scenarios

resource "azapi_resource" "ai_search" {
  count = var.enable_ai_search ? 1 : 0

  type      = "Microsoft.Search/searchServices@2024-06-01-preview"
  name      = "srch-${local.service_resource_name_suffix}-${random_string.suffix.result}"
  location  = data.azurerm_resource_group.ws.location
  parent_id = data.azurerm_resource_group.ws.id

  identity {
    type = "SystemAssigned"
  }

  body = {
    sku = {
      name = "standard"
    }
    properties = {
      replicaCount        = 1
      partitionCount      = 1
      hostingMode         = "default"
      semanticSearch      = "standard"
      disableLocalAuth    = false
      publicNetworkAccess = var.is_exposed_externally ? "Enabled" : "Disabled"
      networkRuleSet = {
        bypass = "None"
      }
      authOptions = {
        aadOrApiKey = {
          aadAuthFailureMode = "http401WithBearerChallenge"
        }
      }
    }
  }

  schema_validation_enabled = true
  tags                      = local.workspace_service_tags

  timeouts {
    create = "60m"
    update = "60m"
    delete = "30m"
  }

  lifecycle {
    ignore_changes = [tags]
  }
}

# Private endpoint for AI Search
resource "azurerm_private_endpoint" "ai_search" {
  count = var.enable_ai_search && !var.is_exposed_externally ? 1 : 0

  name                = "pe-${azapi_resource.ai_search[0].name}"
  location            = data.azurerm_resource_group.ws.location
  resource_group_name = data.azurerm_resource_group.ws.name
  subnet_id           = data.azurerm_subnet.services.id
  tags                = local.workspace_service_tags

  private_service_connection {
    name                           = "psc-${azapi_resource.ai_search[0].name}"
    private_connection_resource_id = azapi_resource.ai_search[0].id
    is_manual_connection           = false
    subresource_names              = ["searchService"]
  }

  private_dns_zone_group {
    name                 = "dns-${azapi_resource.ai_search[0].name}"
    private_dns_zone_ids = [data.azurerm_private_dns_zone.ai_search.id]
  }

  depends_on = [azapi_resource.ai_search]

  lifecycle {
    ignore_changes = [tags]
  }
}

# Role assignment for AI Foundry to access AI Search
resource "azurerm_role_assignment" "ai_foundry_search_contributor" {
  count = var.enable_ai_search ? 1 : 0

  scope                = azapi_resource.ai_search[0].id
  role_definition_name = "Search Service Contributor"
  principal_id         = azurerm_cognitive_account.ai_foundry.identity[0].principal_id
}

resource "azurerm_role_assignment" "ai_foundry_search_index_contributor" {
  count = var.enable_ai_search ? 1 : 0

  scope                = azapi_resource.ai_search[0].id
  role_definition_name = "Search Index Data Contributor"
  principal_id         = azurerm_cognitive_account.ai_foundry.identity[0].principal_id
}

# Connection from AI Foundry Project to AI Search
# This makes AI Search visible as a knowledge store in the AI Foundry portal
resource "azapi_resource" "ai_search_connection" {
  count = var.enable_ai_search ? 1 : 0

  type      = "Microsoft.CognitiveServices/accounts/projects/connections@2025-04-01-preview"
  name      = "ai-search"
  parent_id = azurerm_cognitive_account_project.default.id

  schema_validation_enabled = false

  body = {
    properties = {
      category = "CognitiveSearch"
      target   = "https://${azapi_resource.ai_search[0].name}.search.windows.net"
      authType = "AAD"
      metadata = {
        ApiVersion = "2024-06-01-preview"
        ResourceId = azapi_resource.ai_search[0].id
      }
    }
  }

  depends_on = [
    azapi_resource.ai_search,
    azurerm_private_endpoint.ai_search,
    azurerm_role_assignment.ai_foundry_search_contributor,
    azurerm_role_assignment.ai_foundry_search_index_contributor,
    azurerm_cognitive_account_project.default
  ]
}
