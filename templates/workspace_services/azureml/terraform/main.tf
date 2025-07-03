resource "azapi_resource" "aml_workspace" {
  type      = "Microsoft.MachineLearningServices/workspaces@2024-10-01-preview"
  name      = local.workspace_name
  location  = data.azurerm_resource_group.ws.location
  parent_id = data.azurerm_resource_group.ws.id
  tags      = local.tre_workspace_service_tags

  lifecycle { ignore_changes = [tags, body.properties.imageBuildCompute] }


  dynamic "identity" {
    for_each = var.enable_cmk_encryption ? [] : [1]
    content {
      type = "SystemAssigned"
    }
  }


  dynamic "identity" {
    for_each = var.enable_cmk_encryption ? [1] : []
    content {
      type         = "SystemAssigned, UserAssigned"
      identity_ids = [data.azurerm_user_assigned_identity.ws_encryption_identity[0].id]
    }
  }

  body = {
    properties = {
      applicationInsights      = azurerm_application_insights.ai.id
      containerRegistry        = azurerm_container_registry.acr.id
      description              = var.description
      friendlyName             = var.display_name
      hbiWorkspace             = true
      keyVault                 = data.azurerm_key_vault.ws.id
      publicNetworkAccess      = var.is_exposed_externally ? "Enabled" : "Disabled"
      storageAccount           = azurerm_storage_account.aml.id
      systemDatastoresAuthMode = "identity"

      workspaceHubConfig = {
        additionalWorkspaceStorageAccounts = []
      }


      encryption = {
        status = var.enable_cmk_encryption ? "Enabled" : "Disabled"
        identity = {
          userAssignedIdentity = var.enable_cmk_encryption ? data.azurerm_user_assigned_identity.ws_encryption_identity[0].id : null
        }
        keyVaultProperties = {
          keyIdentifier    = var.enable_cmk_encryption ? data.azurerm_key_vault_key.ws_encryption_key[0].versionless_id : null
          keyVaultArmId    = var.enable_cmk_encryption ? var.key_store_id : null
          identityClientId = var.enable_cmk_encryption ? data.azurerm_user_assigned_identity.ws_encryption_identity[0].client_id : null
        }
      }
    }
  }

  response_export_values = ["id", "name", "identity.principalId"]
}

resource "azurerm_private_endpoint" "mlpe" {
  name                = "mlpe-${local.service_resource_name_suffix}"
  location            = data.azurerm_resource_group.ws.location
  resource_group_name = data.azurerm_resource_group.ws.name
  subnet_id           = azurerm_subnet.aml.id
  tags                = local.tre_workspace_service_tags

  lifecycle { ignore_changes = [tags] }

  private_dns_zone_group {
    name                 = "private-dns-zone-group"
    private_dns_zone_ids = [data.azurerm_private_dns_zone.azureml.id, data.azurerm_private_dns_zone.notebooks.id, data.azurerm_private_dns_zone.azuremlcert.id]
  }

  private_service_connection {
    name                           = "mlpesc-${local.service_resource_name_suffix}"
    private_connection_resource_id = azapi_resource.aml_workspace.output.id
    is_manual_connection           = false
    subresource_names              = ["amlworkspace"]
  }

  depends_on = [
    azurerm_subnet_network_security_group_association.aml,
    azapi_resource.aml_service_endpoint_policy
  ]

}

resource "azurerm_application_insights" "ai" {
  name                = "ai-${local.service_resource_name_suffix}"
  location            = data.azurerm_resource_group.ws.location
  resource_group_name = data.azurerm_resource_group.ws.name
  application_type    = "web"
  workspace_id        = data.azurerm_log_analytics_workspace.ws.id
  tags                = local.tre_workspace_service_tags

  lifecycle { ignore_changes = [tags] }
}
