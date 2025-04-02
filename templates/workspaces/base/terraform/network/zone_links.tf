resource "azurerm_private_dns_zone_virtual_network_link" "azurewebsites" {
  provider              = azurerm.core
  name                  = "azurewebsites-link-${azurerm_virtual_network.ws.name}"
  resource_group_name   = local.core_resource_group_name
  private_dns_zone_name = data.azurerm_private_dns_zone.azurewebsites.name
  virtual_network_id    = azurerm_virtual_network.ws.id
  registration_enabled  = false
  tags                  = var.tre_workspace_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "filecorelink" {
  provider              = azurerm.core
  name                  = "filecorelink-${local.workspace_resource_name_suffix}"
  resource_group_name   = local.core_resource_group_name
  private_dns_zone_name = data.azurerm_private_dns_zone.filecore.name
  virtual_network_id    = azurerm_virtual_network.ws.id
  tags                  = var.tre_workspace_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "blobcorelink" {
  provider              = azurerm.core
  name                  = "blobcorelink-${local.workspace_resource_name_suffix}"
  resource_group_name   = local.core_resource_group_name
  private_dns_zone_name = data.azurerm_private_dns_zone.blobcore.name
  virtual_network_id    = azurerm_virtual_network.ws.id
  tags                  = var.tre_workspace_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "dfscorelink" {
  provider              = azurerm.core
  name                  = "dfscorelink-${local.workspace_resource_name_suffix}"
  resource_group_name   = local.core_resource_group_name
  private_dns_zone_name = data.azurerm_private_dns_zone.dfscore.name
  virtual_network_id    = azurerm_virtual_network.ws.id
  tags                  = var.tre_workspace_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "vaultcorelink" {
  provider              = azurerm.core
  name                  = "vaultcorelink-${local.workspace_resource_name_suffix}"
  resource_group_name   = local.core_resource_group_name
  private_dns_zone_name = data.azurerm_private_dns_zone.vaultcore.name
  virtual_network_id    = azurerm_virtual_network.ws.id
  tags                  = var.tre_workspace_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "azurecrlink" {
  provider              = azurerm.core
  name                  = "azurecrlink-${local.workspace_resource_name_suffix}"
  resource_group_name   = local.core_resource_group_name
  private_dns_zone_name = data.azurerm_private_dns_zone.azurecr.name
  virtual_network_id    = azurerm_virtual_network.ws.id
  tags                  = var.tre_workspace_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "azuremllink" {
  provider              = azurerm.core
  name                  = "azuremllink-${local.workspace_resource_name_suffix}"
  resource_group_name   = local.core_resource_group_name
  private_dns_zone_name = data.azurerm_private_dns_zone.azureml.name
  virtual_network_id    = azurerm_virtual_network.ws.id
  tags                  = var.tre_workspace_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "azuremlcertlink" {
  provider              = azurerm.core
  name                  = "azuremlcertlink-${local.workspace_resource_name_suffix}"
  resource_group_name   = local.core_resource_group_name
  private_dns_zone_name = data.azurerm_private_dns_zone.azuremlcert.name
  virtual_network_id    = azurerm_virtual_network.ws.id
  tags                  = var.tre_workspace_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "healthlink" {
  provider              = azurerm.core
  name                  = "healthlink-${local.workspace_resource_name_suffix}"
  resource_group_name   = local.core_resource_group_name
  private_dns_zone_name = data.azurerm_private_dns_zone.health.name
  virtual_network_id    = azurerm_virtual_network.ws.id
  tags                  = var.tre_workspace_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "dicomlink" {
  provider              = azurerm.core
  name                  = "dicomlink-${local.workspace_resource_name_suffix}"
  resource_group_name   = local.core_resource_group_name
  private_dns_zone_name = data.azurerm_private_dns_zone.dicom.name
  virtual_network_id    = azurerm_virtual_network.ws.id
  tags                  = var.tre_workspace_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "notebookslink" {
  provider              = azurerm.core
  name                  = "notebookslink-${local.workspace_resource_name_suffix}"
  resource_group_name   = local.core_resource_group_name
  private_dns_zone_name = data.azurerm_private_dns_zone.notebooks.name
  virtual_network_id    = azurerm_virtual_network.ws.id
  tags                  = var.tre_workspace_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "mysqllink" {
  provider              = azurerm.core
  name                  = "mysqllink-${local.workspace_resource_name_suffix}"
  resource_group_name   = local.core_resource_group_name
  private_dns_zone_name = data.azurerm_private_dns_zone.mysql.name
  virtual_network_id    = azurerm_virtual_network.ws.id
  tags                  = var.tre_workspace_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "postgreslink" {
  provider              = azurerm.core
  name                  = "postgreslink-${local.workspace_resource_name_suffix}"
  resource_group_name   = local.core_resource_group_name
  private_dns_zone_name = data.azurerm_private_dns_zone.postgres.name
  virtual_network_id    = azurerm_virtual_network.ws.id
  tags                  = var.tre_workspace_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "azuresqllink" {
  provider              = azurerm.core
  name                  = "azuresqllink-${local.workspace_resource_name_suffix}"
  resource_group_name   = local.core_resource_group_name
  private_dns_zone_name = data.azurerm_private_dns_zone.azuresql.name
  virtual_network_id    = azurerm_virtual_network.ws.id
  tags                  = var.tre_workspace_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "nexuslink" {
  provider              = azurerm.core
  name                  = "nexuslink-${local.workspace_resource_name_suffix}"
  resource_group_name   = local.core_resource_group_name
  private_dns_zone_name = data.azurerm_private_dns_zone.nexus.name
  virtual_network_id    = azurerm_virtual_network.ws.id
  tags                  = var.tre_workspace_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "databrickslink" {
  provider              = azurerm.core
  name                  = "databrickslink-${local.workspace_resource_name_suffix}"
  resource_group_name   = local.core_resource_group_name
  private_dns_zone_name = data.azurerm_private_dns_zone.databricks.name
  virtual_network_id    = azurerm_virtual_network.ws.id
  tags                  = var.tre_workspace_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "openailink" {
  provider              = azurerm.core
  name                  = "openailink-${local.workspace_resource_name_suffix}"
  resource_group_name   = local.core_resource_group_name
  private_dns_zone_name = data.azurerm_private_dns_zone.openai.name
  virtual_network_id    = azurerm_virtual_network.ws.id
  tags                  = var.tre_workspace_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "cognitveserviceslink" {
  provider              = azurerm.core
  name                  = "cognitiveserviceslink-${local.workspace_resource_name_suffix}"
  resource_group_name   = local.core_resource_group_name
  private_dns_zone_name = data.azurerm_private_dns_zone.cognitiveservices.name
  virtual_network_id    = azurerm_virtual_network.ws.id
  tags                  = var.tre_workspace_tags

  lifecycle { ignore_changes = [tags] }
}
