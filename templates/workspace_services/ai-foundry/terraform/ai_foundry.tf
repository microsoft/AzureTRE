# AI Foundry (AIServices) Account
# Using azurerm_cognitive_account which properly handles LRO and waits for provisioningState=Succeeded

resource "random_string" "suffix" {
  length  = 5
  lower   = true
  upper   = false
  numeric = true
  special = false
}

# Create AI Foundry account using azurerm provider
# azurerm properly waits for account provisioning to complete before returning
resource "azurerm_cognitive_account" "ai_foundry" {
  name                          = "aif-${local.service_resource_name_suffix}"
  location                      = data.azurerm_resource_group.ws.location
  resource_group_name           = data.azurerm_resource_group.ws.name
  kind                          = "AIServices"
  sku_name                      = "S0"
  custom_subdomain_name         = "aif-${local.service_resource_name_suffix}"
  public_network_access_enabled = var.is_exposed_externally
  local_auth_enabled            = true
  project_management_enabled    = true

  identity {
    type = "SystemAssigned"
  }

  network_acls {
    default_action = "Allow"
  }

  # Network injection for agent networking (optional)
  dynamic "network_injection" {
    for_each = var.enable_agent_networking ? [1] : []
    content {
      scenario  = "agent"
      subnet_id = azurerm_subnet.agents.id
    }
  }

  tags = local.workspace_service_tags

  timeouts {
    create = "60m"
    update = "60m"
    delete = "30m"
    read   = "5m"
  }

  lifecycle {
    ignore_changes = [tags]
  }
}

# Wait for AIServices to fully provision internally
# The azurerm provider returns before Azure has fully completed internal provisioning
# for AIServices with project_management_enabled=true
resource "time_sleep" "wait_for_ai_foundry" {
  depends_on      = [azurerm_cognitive_account.ai_foundry]
  create_duration = "600s" # 10 minutes

  triggers = {
    account_id = azurerm_cognitive_account.ai_foundry.id
  }
}

# Private endpoint for AI Foundry
resource "azurerm_private_endpoint" "ai_foundry" {
  count = var.is_exposed_externally ? 0 : 1

  name                = "pe-aif-${local.service_resource_name_suffix}"
  location            = data.azurerm_resource_group.ws.location
  resource_group_name = data.azurerm_resource_group.ws.name
  subnet_id           = data.azurerm_subnet.services.id
  tags                = local.workspace_service_tags

  private_service_connection {
    name                           = "psc-aif-${local.service_resource_name_suffix}"
    private_connection_resource_id = azurerm_cognitive_account.ai_foundry.id
    is_manual_connection           = false
    subresource_names              = ["account"]
  }

  depends_on = [time_sleep.wait_for_ai_foundry]

  private_dns_zone_group {
    name = "dns-aif-${local.service_resource_name_suffix}"
    private_dns_zone_ids = [
      data.azurerm_private_dns_zone.cognitive_services.id,
      data.azurerm_private_dns_zone.openai.id,
      data.azurerm_private_dns_zone.ai_services.id
    ]
  }

  timeouts {
    create = "30m"
    update = "30m"
    delete = "30m"
    read   = "5m"
  }

  lifecycle {
    ignore_changes = [tags]
  }
}

# Default AI Foundry Project - required for connections and portal access
resource "azurerm_cognitive_account_project" "default" {
  name                 = "default"
  cognitive_account_id = azurerm_cognitive_account.ai_foundry.id
  location             = data.azurerm_resource_group.ws.location
  display_name         = "Default Project"

  identity {
    type = "SystemAssigned"
  }

  depends_on = [azurerm_private_endpoint.ai_foundry]

  timeouts {
    create = "30m"
    update = "30m"
    delete = "30m"
    read   = "5m"
  }
}

# OpenAI Model Deployment
resource "azurerm_cognitive_deployment" "openai" {
  name                 = local.openai_model.name
  cognitive_account_id = azurerm_cognitive_account.ai_foundry.id

  model {
    format  = "OpenAI"
    name    = local.openai_model.name
    version = local.openai_model.version
  }

  sku {
    name     = "Standard"
    capacity = var.openai_model_capacity
  }

  timeouts {
    create = "30m"
    update = "30m"
    delete = "30m"
    read   = "5m"
  }
}

# Storage container for AI Foundry artifacts (unique per service instance)
resource "azurerm_storage_container" "ai_foundry" {
  name                  = "aif-${random_string.suffix.result}"
  storage_account_id    = data.azurerm_storage_account.workspace.id
  container_access_type = "private"
}

# Connection from AI Foundry Project to Workspace Storage
# This makes the storage account visible in the AI Foundry portal
resource "azapi_resource" "storage_connection" {
  type      = "Microsoft.CognitiveServices/accounts/projects/connections@2025-04-01-preview"
  name      = "workspace-storage"
  parent_id = azurerm_cognitive_account_project.default.id

  schema_validation_enabled = false

  body = {
    properties = {
      category = "AzureBlob"
      target   = data.azurerm_storage_account.workspace.primary_blob_endpoint
      authType = "AAD"
      metadata = {
        ResourceId    = data.azurerm_storage_account.workspace.id
        AccountName   = data.azurerm_storage_account.workspace.name
        ContainerName = azurerm_storage_container.ai_foundry.name
      }
    }
  }

  depends_on = [
    azurerm_cognitive_account_project.default,
    azurerm_storage_container.ai_foundry
  ]
}

# Role assignment for AI Foundry to access workspace storage
resource "azurerm_role_assignment" "ai_foundry_storage_blob_contributor" {
  scope                = data.azurerm_storage_account.workspace.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_cognitive_account.ai_foundry.identity[0].principal_id
}

resource "azurerm_role_assignment" "ai_foundry_storage_file_contributor" {
  scope                = data.azurerm_storage_account.workspace.id
  role_definition_name = "Storage File Data Privileged Contributor"
  principal_id         = azurerm_cognitive_account.ai_foundry.identity[0].principal_id
}
