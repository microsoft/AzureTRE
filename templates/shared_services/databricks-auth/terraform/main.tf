resource "azurerm_resource_group" "rg" {
  location = data.azurerm_resource_group.rg.location
  name     = local.resource_group_name
  tags = merge(
    local.tre_shared_service_tags,
    {
      project = "Azure Trusted Research Environment",
      source  = "https://github.com/microsoft/AzureTRE/"
    },
  )

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_databricks_workspace" "databricks" {
  name                                  = local.databricks_workspace_name
  resource_group_name                   = local.resource_group_name
  location                              = azurerm_resource_group.rg.location
  sku                                   = "premium"
  managed_resource_group_name           = local.managed_resource_group_name
  infrastructure_encryption_enabled     = true
  public_network_access_enabled         = false
  network_security_group_rules_required = "NoAzureDatabricksRules"
  default_storage_firewall_enabled      = true
  access_connector_id                   = azurerm_databricks_access_connector.connector.id
  tags                                  = local.tre_shared_service_tags

  lifecycle { ignore_changes = [tags] }

  custom_parameters {
    no_public_ip                                         = true
    public_subnet_name                                   = azurerm_subnet.host.name
    private_subnet_name                                  = azurerm_subnet.container.name
    virtual_network_id                                   = azurerm_virtual_network.ws.id
    public_subnet_network_security_group_association_id  = azurerm_subnet_network_security_group_association.host.id
    private_subnet_network_security_group_association_id = azurerm_subnet_network_security_group_association.container.id
  }

  depends_on = [
    azurerm_subnet_network_security_group_association.host,
    azurerm_subnet_network_security_group_association.container
  ]
}

// required to set default_storage_firewall_enabled = true
// https://learn.microsoft.com/en-us/azure/databricks/security/network/storage/firewall-support
//
resource "azurerm_databricks_access_connector" "connector" {
  name                = "${local.databricks_workspace_name}-access-connector"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  tags                = local.tre_shared_service_tags

  identity {
    type = "SystemAssigned"
  }

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_monitor_diagnostic_setting" "databricks_diagnostics" {
  name                       = "diagnostics-${local.databricks_workspace_name}"
  target_resource_id         = azurerm_databricks_workspace.databricks.id
  log_analytics_workspace_id = data.azurerm_log_analytics_workspace.tre.id

  enabled_log {
    category = "accounts"
  }

  enabled_log {
    category = "workspace"
  }

  enabled_log {
    category = "gitCredentials"
  }

  enabled_log {
    category = "iamRole"
  }

  enabled_log {
    category = "secrets"
  }
}
