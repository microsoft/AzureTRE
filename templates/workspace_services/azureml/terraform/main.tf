data "azurerm_resource_group" "ws" {
  name = "rg-${var.tre_id}-ws-${local.short_workspace_id}"
}

data "azurerm_virtual_network" "ws" {
  name                = "vnet-${var.tre_id}-ws-${local.short_workspace_id}"
  resource_group_name = data.azurerm_resource_group.ws.name
}

data "azurerm_subnet" "services" {
  name                 = "ServicesSubnet"
  virtual_network_name = data.azurerm_virtual_network.ws.name
  resource_group_name  = data.azurerm_virtual_network.ws.resource_group_name
}

resource "azurerm_application_insights" "ai" {
  name                = "ai-${local.service_resource_name_suffix}"
  location            = data.azurerm_resource_group.ws.location
  resource_group_name = data.azurerm_resource_group.ws.name
  application_type    = "web"
  tags                = local.tre_workspace_service_tags

  lifecycle { ignore_changes = [tags] }
}

data "azurerm_key_vault" "ws" {
  name                = local.keyvault_name
  resource_group_name = data.azurerm_resource_group.ws.name
}

# Using AzAPI due to https://github.com/hashicorp/terraform-provider-azurerm/issues/16177
resource "azapi_resource" "aml_workspace" {
  name                      = local.workspace_name
  parent_id                 = data.azurerm_resource_group.ws.id
  type                      = "Microsoft.MachineLearningServices/workspaces@2022-05-01"
  schema_validation_enabled = false
  location                  = data.azurerm_resource_group.ws.location

  body = jsonencode({
    properties = {
      allowRecoverSoftDeletedWorkspace = "True"
      applicationInsights              = azurerm_application_insights.ai.id
      containerRegistry                = azurerm_container_registry.acr.id
      friendlyName                     = var.display_name
      description                      = var.description
      hbiWorkspace                     = true
      keyVault                         = data.azurerm_key_vault.ws.id
      publicNetworkAccess              = var.is_exposed_externally ? "Enabled" : "Disabled"
      storageAccount                   = azurerm_storage_account.aml.id
      v1LegacyMode                     = false
    }
    identity = {
      type = "SystemAssigned"
    }
  })

  response_export_values = ["*"]

}

data "azurerm_private_dns_zone" "azureml" {
  name                = "privatelink.api.azureml.ms"
  resource_group_name = local.core_resource_group_name
}

data "azurerm_private_dns_zone" "azuremlcert" {
  name                = "privatelink.cert.api.azureml.ms"
  resource_group_name = local.core_resource_group_name
}


data "azurerm_private_dns_zone" "notebooks" {
  name                = "privatelink.notebooks.azure.net"
  resource_group_name = local.core_resource_group_name
}
resource "azurerm_private_endpoint" "mlpe" {
  name                = "mlpe-${local.service_resource_name_suffix}"
  location            = data.azurerm_resource_group.ws.location
  resource_group_name = data.azurerm_resource_group.ws.name
  subnet_id           = data.azurerm_subnet.services.id
  tags                = local.tre_workspace_service_tags

  lifecycle { ignore_changes = [tags] }

  private_dns_zone_group {
    name                 = "private-dns-zone-group"
    private_dns_zone_ids = [data.azurerm_private_dns_zone.azureml.id, data.azurerm_private_dns_zone.notebooks.id, data.azurerm_private_dns_zone.azuremlcert.id]
  }

  private_service_connection {
    name                           = "mlpesc-${local.service_resource_name_suffix}"
    private_connection_resource_id = azapi_resource.aml_workspace.id
    is_manual_connection           = false
    subresource_names              = ["amlworkspace"]
  }
}
