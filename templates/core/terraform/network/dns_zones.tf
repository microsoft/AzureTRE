
resource "azurerm_private_dns_zone" "azurewebsites" {
  name                = "privatelink.azurewebsites.net"
  resource_group_name = var.resource_group_name

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "azurewebsites" {
  resource_group_name   = var.resource_group_name
  virtual_network_id    = azurerm_virtual_network.core.id
  private_dns_zone_name = azurerm_private_dns_zone.azurewebsites.name
  name                  = "azurewebsites-link"
  registration_enabled  = false

  lifecycle { ignore_changes = [tags] }
}


resource "azurerm_private_dns_zone" "mysql" {
  name                = "privatelink.mysql.database.azure.com"
  resource_group_name = var.resource_group_name

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "mysql" {
  resource_group_name   = var.resource_group_name
  virtual_network_id    = azurerm_virtual_network.core.id
  private_dns_zone_name = azurerm_private_dns_zone.mysql.name
  name                  = "azurewebsites-link"
  registration_enabled  = false

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone" "static_web" {
  name                = "privatelink.web.core.windows.net"
  resource_group_name = var.resource_group_name

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "webcorelink" {
  name                  = "staticwebcorelink"
  resource_group_name   = var.resource_group_name
  private_dns_zone_name = azurerm_private_dns_zone.static_web.name
  virtual_network_id    = azurerm_virtual_network.core.id

  lifecycle { ignore_changes = [tags] }
}


resource "azurerm_private_dns_zone" "filecore" {
  name                = "privatelink.file.core.windows.net"
  resource_group_name = var.resource_group_name

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "filecorelink" {
  name                  = "filecorelink"
  resource_group_name   = var.resource_group_name
  private_dns_zone_name = azurerm_private_dns_zone.filecore.name
  virtual_network_id    = azurerm_virtual_network.core.id

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone" "blobcore" {
  name                = "privatelink.blob.core.windows.net"
  resource_group_name = var.resource_group_name

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "blobcore" {
  name                  = "blobcorelink"
  resource_group_name   = var.resource_group_name
  private_dns_zone_name = azurerm_private_dns_zone.blobcore.name
  virtual_network_id    = azurerm_virtual_network.core.id

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone" "vaultcore" {
  name                = "privatelink.vaultcore.azure.net"
  resource_group_name = var.resource_group_name

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "vaultcore" {
  name                  = "vaultcorelink"
  resource_group_name   = var.resource_group_name
  private_dns_zone_name = azurerm_private_dns_zone.vaultcore.name
  virtual_network_id    = azurerm_virtual_network.core.id

  lifecycle { ignore_changes = [tags] }
}


resource "azurerm_private_dns_zone" "azurecr" {
  name                = "privatelink.azurecr.io"
  resource_group_name = var.resource_group_name

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "acrlink" {
  name                  = "acrcorelink"
  resource_group_name   = var.resource_group_name
  private_dns_zone_name = azurerm_private_dns_zone.azurecr.name
  virtual_network_id    = azurerm_virtual_network.core.id

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone" "azureml" {
  name                = "privatelink.api.azureml.ms"
  resource_group_name = var.resource_group_name

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone" "azuremlcert" {
  name                = "privatelink.cert.api.azureml.ms"
  resource_group_name = var.resource_group_name

  lifecycle { ignore_changes = [tags] }
}


resource "azurerm_private_dns_zone" "notebooks" {
  name                = "privatelink.notebooks.azure.net"
  resource_group_name = var.resource_group_name

  lifecycle { ignore_changes = [tags] }
}