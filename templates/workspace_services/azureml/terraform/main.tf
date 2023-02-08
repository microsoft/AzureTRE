resource "azurerm_machine_learning_workspace" "aml_workspace" {
  name                          = local.workspace_name
  resource_group_name           = data.azurerm_resource_group.ws.name
  location                      = data.azurerm_resource_group.ws.location
  application_insights_id       = azurerm_application_insights.ai.id
  container_registry_id         = azurerm_container_registry.acr.id
  friendly_name                 = var.display_name
  description                   = var.description
  high_business_impact          = true
  key_vault_id                  = data.azurerm_key_vault.ws.id
  public_network_access_enabled = var.is_exposed_externally ? true : false
  storage_account_id            = azurerm_storage_account.aml.id
  tags                          = local.tre_workspace_service_tags

  identity {
    type = "SystemAssigned"
  }

  lifecycle {
    ignore_changes = [
      tags,
      image_build_compute_name,
      public_access_behind_virtual_network_enabled
    ]
  }

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
    private_connection_resource_id = azurerm_machine_learning_workspace.aml_workspace.id
    is_manual_connection           = false
    subresource_names              = ["amlworkspace"]
  }

  depends_on = [
    azurerm_subnet_network_security_group_association.aml,
    azapi_resource.aml_service_endpoint_policy
  ]

}
