resource "azurerm_databricks_workspace" "databricks" {
  name                              = local.databricks_workspace_name
  resource_group_name               = data.azurerm_resource_group.rg.name
  location                          = data.azurerm_resource_group.rg.location
  sku                               = "premium"
  managed_resource_group_name       = local.managed_resource_group_name
  infrastructure_encryption_enabled = true

  tags = local.tags
  lifecycle { ignore_changes = [tags] }

  custom_parameters {
    no_public_ip        = true
    public_subnet_name  = azurerm_subnet.public.name
    private_subnet_name = azurerm_subnet.private.name
    virtual_network_id  = data.azurerm_virtual_network.vnet.id

    public_subnet_network_security_group_association_id  = azurerm_subnet_network_security_group_association.public.id
    private_subnet_network_security_group_association_id = azurerm_subnet_network_security_group_association.private.id
  }
}

provider "databricks" {
  host = azurerm_databricks_workspace.databricks.workspace_url
}

resource "databricks_workspace_conf" "databricks-ws" {
  custom_config = {
    "enableIpAccessLists" : true
  }
  depends_on = [azurerm_databricks_workspace.databricks]
}

resource "databricks_ip_access_list" "allowed-list" {
  label     = "allow_in"
  list_type = "ALLOW"
  ip_addresses = [
    "${data.azurerm_public_ip.firewall-public-ip.ip_address}/32",
    "${chomp(data.http.myip.body)}/32"
  ]
  depends_on = [databricks_workspace_conf.databricks-ws]
}
