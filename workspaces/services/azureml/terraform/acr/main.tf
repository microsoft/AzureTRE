
data "azurerm_resource_group" "ws" {
  name = "rg-${var.tre_id}-ws-${var.workspace_id}"
}

data "azurerm_virtual_network" "ws" {
  name                = "vnet-${var.tre_id}-ws-${var.workspace_id}"
  resource_group_name = data.azurerm_resource_group.ws.name
}

data "azurerm_subnet" "services" {
  name                 = "ServicesSubnet"
  virtual_network_name = data.azurerm_virtual_network.ws.name
  resource_group_name  = data.azurerm_virtual_network.ws.resource_group_name
}

locals {
  acr_name             = lower(replace("acr${substr(local.service_resource_name_suffix, -8, -1)}", "-", ""))
  service_resource_name_suffix = "${var.tre_id}-ws-${var.workspace_id}-svc-${var.service_id}"
}
resource "azurerm_container_registry" "acr" {
  name                     = local.acr_name
  location                 = data.azurerm_resource_group.ws.location
  resource_group_name      = data.azurerm_resource_group.ws.name
  sku                      = "Premium"
  admin_enabled            = false

  lifecycle { ignore_changes = [ tags ] }
}

resource "azurerm_private_dns_zone" "azurecr" {
  name                = "privatelink.azurecr.io"
  resource_group_name = data.azurerm_resource_group.ws.name

  lifecycle { ignore_changes = [ tags ] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "azurecrlink" {
  name                  = "azurecrlink-${local.service_resource_name_suffix}"
  resource_group_name   = data.azurerm_resource_group.ws.name
  private_dns_zone_name = azurerm_private_dns_zone.azurecr.name
  virtual_network_id    = data.azurerm_virtual_network.ws.id

  lifecycle { ignore_changes = [ tags ] }
}

resource "azurerm_private_endpoint" "acrpe" {
  name                = "acrpe-${local.service_resource_name_suffix}"
  location            =data.azurerm_resource_group.ws.location
  resource_group_name   = data.azurerm_resource_group.ws.name
  subnet_id           = data.azurerm_subnet.services.id

  lifecycle { ignore_changes = [ tags ] }

  private_dns_zone_group {
    name                 = "private-dns-zone-group"
    private_dns_zone_ids = [azurerm_private_dns_zone.azurecr.id]
  }

  private_service_connection {
    name                           = "acrpesc-${local.service_resource_name_suffix}"
    private_connection_resource_id = azurerm_container_registry.acr.id
    is_manual_connection           = false
    subresource_names              = ["registry"]
  }
}