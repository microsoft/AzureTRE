resource "azurerm_private_dns_zone_virtual_network_link" "azurewebsites" {
  name                  = "azurewebsites-link-${azurerm_virtual_network.ws.name}"
  resource_group_name   = local.core_resource_group_name
  private_dns_zone_name = data.azurerm_private_dns_zone.azurewebsites.name
  virtual_network_id    = azurerm_virtual_network.ws.id
  registration_enabled  = false
  tags                  = var.tre_workspace_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "filecorelink" {
  name                  = "filecorelink-${local.workspace_resource_name_suffix}"
  resource_group_name   = local.core_resource_group_name
  private_dns_zone_name = data.azurerm_private_dns_zone.filecore.name
  virtual_network_id    = azurerm_virtual_network.ws.id
  tags                  = var.tre_workspace_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "blobcorelink" {
  name                  = "blobcorelink-${local.workspace_resource_name_suffix}"
  resource_group_name   = local.core_resource_group_name
  private_dns_zone_name = data.azurerm_private_dns_zone.blobcore.name
  virtual_network_id    = azurerm_virtual_network.ws.id
  tags                  = var.tre_workspace_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "dfscorelink" {
  name                  = "dfscorelink-${local.workspace_resource_name_suffix}"
  resource_group_name   = local.core_resource_group_name
  private_dns_zone_name = data.azurerm_private_dns_zone.dfscore.name
  virtual_network_id    = azurerm_virtual_network.ws.id
  tags                  = var.tre_workspace_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "vaultcorelink" {
  name                  = "vaultcorelink-${local.workspace_resource_name_suffix}"
  resource_group_name   = local.core_resource_group_name
  private_dns_zone_name = data.azurerm_private_dns_zone.vaultcore.name
  virtual_network_id    = azurerm_virtual_network.ws.id
  tags                  = var.tre_workspace_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "azurecrlink" {
  name                  = "azurecrlink-${local.workspace_resource_name_suffix}"
  resource_group_name   = local.core_resource_group_name
  private_dns_zone_name = data.azurerm_private_dns_zone.azurecr.name
  virtual_network_id    = azurerm_virtual_network.ws.id
  tags                  = var.tre_workspace_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "azuremllink" {
  name                  = "azuremllink-${local.workspace_resource_name_suffix}"
  resource_group_name   = local.core_resource_group_name
  private_dns_zone_name = data.azurerm_private_dns_zone.azureml.name
  virtual_network_id    = azurerm_virtual_network.ws.id
  tags                  = var.tre_workspace_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "azuremlcertlink" {
  name                  = "azuremlcertlink-${local.workspace_resource_name_suffix}"
  resource_group_name   = local.core_resource_group_name
  private_dns_zone_name = data.azurerm_private_dns_zone.azuremlcert.name
  virtual_network_id    = azurerm_virtual_network.ws.id
  tags                  = var.tre_workspace_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "healthlink" {
  name                  = "healthlink-${local.workspace_resource_name_suffix}"
  resource_group_name   = local.core_resource_group_name
  private_dns_zone_name = data.azurerm_private_dns_zone.health.name
  virtual_network_id    = azurerm_virtual_network.ws.id
  tags                  = var.tre_workspace_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "dicomlink" {
  name                  = "dicomlink-${local.workspace_resource_name_suffix}"
  resource_group_name   = local.core_resource_group_name
  private_dns_zone_name = data.azurerm_private_dns_zone.dicom.name
  virtual_network_id    = azurerm_virtual_network.ws.id
  tags                  = var.tre_workspace_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "notebookslink" {
  name                  = "notebookslink-${local.workspace_resource_name_suffix}"
  resource_group_name   = local.core_resource_group_name
  private_dns_zone_name = data.azurerm_private_dns_zone.notebooks.name
  virtual_network_id    = azurerm_virtual_network.ws.id
  tags                  = var.tre_workspace_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "mysqllink" {
  name                  = "mysqllink-${local.workspace_resource_name_suffix}"
  resource_group_name   = local.core_resource_group_name
  private_dns_zone_name = data.azurerm_private_dns_zone.mysql.name
  virtual_network_id    = azurerm_virtual_network.ws.id
  tags                  = var.tre_workspace_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "postgreslink" {
  name                  = "postgreslink-${local.workspace_resource_name_suffix}"
  resource_group_name   = local.core_resource_group_name
  private_dns_zone_name = data.azurerm_private_dns_zone.postgres.name
  virtual_network_id    = azurerm_virtual_network.ws.id
  tags                  = var.tre_workspace_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "nexuslink" {
  name                  = "nexuslink-${local.workspace_resource_name_suffix}"
  resource_group_name   = local.core_resource_group_name
  private_dns_zone_name = data.azurerm_private_dns_zone.nexus.name
  virtual_network_id    = azurerm_virtual_network.ws.id
  tags                  = var.tre_workspace_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "databrickslink" {
  name                  = "databrickslink-${local.workspace_resource_name_suffix}"
  resource_group_name   = local.core_resource_group_name
  private_dns_zone_name = data.azurerm_private_dns_zone.databricks.name
  virtual_network_id    = azurerm_virtual_network.ws.id
  tags                  = var.tre_workspace_tags

  lifecycle { ignore_changes = [tags] }
}
