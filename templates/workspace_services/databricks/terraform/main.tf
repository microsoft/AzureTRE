resource "azurerm_databricks_workspace" "databricks" {
  name                              = local.databricks_workspace_name
  resource_group_name               = data.azurerm_resource_group.rg.name
  location                          = data.azurerm_resource_group.rg.location
  sku                               = "premium"
  managed_resource_group_name       = local.managed_resource_group_name
  infrastructure_encryption_enabled = true
  public_network_access_enabled     = var.is_exposed_externally
  network_security_group_rules_required = var.is_exposed_externally ? "AllRules" : "NoAzureDatabricksRules"

  tags = local.tre_workspace_service_tags
  lifecycle { ignore_changes = [tags] }

  custom_parameters {
    no_public_ip        = true
    public_subnet_name  = azurerm_subnet.public.name
    private_subnet_name = azurerm_subnet.private.name
    virtual_network_id  = data.azurerm_virtual_network.ws.id

    public_subnet_network_security_group_association_id  = azurerm_subnet_network_security_group_association.public.id
    private_subnet_network_security_group_association_id = azurerm_subnet_network_security_group_association.private.id
  }

  depends_on = [
    azurerm_subnet_network_security_group_association.public,
    azurerm_subnet_network_security_group_association.private
  ]
}
