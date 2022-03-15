resource "azurerm_virtual_network" "ws" {
  name                = "vnet-${local.workspace_resource_name_suffix}"
  location            = var.location
  resource_group_name = azurerm_resource_group.ws.name
  address_space       = [var.address_space]

  lifecycle { ignore_changes = [tags] }
}


resource "azurerm_subnet" "services" {
  name                 = "ServicesSubnet"
  virtual_network_name = azurerm_virtual_network.ws.name
  resource_group_name  = azurerm_resource_group.ws.name
  address_prefixes     = [local.services_subnet_address_prefix]
  # notice that private endpoints do not adhere to NSG rules
  enforce_private_link_endpoint_network_policies = true
  enforce_private_link_service_network_policies  = true
}

resource "azurerm_subnet" "webapps" {
  name                 = "WebAppsSubnet"
  virtual_network_name = azurerm_virtual_network.ws.name
  resource_group_name  = azurerm_resource_group.ws.name
  address_prefixes     = [local.webapps_subnet_address_prefix]
  # notice that private endpoints do not adhere to NSG rules
  enforce_private_link_endpoint_network_policies = true
  enforce_private_link_service_network_policies  = true

  delegation {
    name = "delegation"

    service_delegation {
      name    = "Microsoft.Web/serverFarms"
      actions = ["Microsoft.Network/virtualNetworks/subnets/action"]
    }
  }
}

data "azurerm_virtual_network" "core" {
  name                = local.core_vnet
  resource_group_name = local.core_resource_group_name
}

data "azurerm_subnet" "core_webapps" {
  name                 = "WebAppSubnet"
  virtual_network_name = "vnet-${var.tre_id}"
  resource_group_name  = "rg-${var.tre_id}"
}

resource "azurerm_virtual_network_peering" "ws-core-peer" {
  name                      = "ws-core-peer-${local.workspace_resource_name_suffix}"
  resource_group_name       = azurerm_resource_group.ws.name
  virtual_network_name      = azurerm_virtual_network.ws.name
  remote_virtual_network_id = data.azurerm_virtual_network.core.id
}

resource "azurerm_virtual_network_peering" "core-ws-peer" {
  name                      = "core-ws-peer-${local.workspace_resource_name_suffix}"
  resource_group_name       = local.core_resource_group_name
  virtual_network_name      = local.core_vnet
  remote_virtual_network_id = azurerm_virtual_network.ws.id
}

data "azurerm_subnet" "shared" {
  resource_group_name  = local.core_resource_group_name
  virtual_network_name = local.core_vnet
  name                 = "SharedSubnet"
}

data "azurerm_subnet" "bastion" {
  resource_group_name  = local.core_resource_group_name
  virtual_network_name = local.core_vnet
  name                 = "AzureBastionSubnet"
}

data "azurerm_subnet" "resourceprocessor" {
  resource_group_name  = local.core_resource_group_name
  virtual_network_name = local.core_vnet
  name                 = "ResourceProcessorSubnet"
}

resource "azurerm_network_security_group" "ws" {
  location            = var.location
  name                = "nsg-ws"
  resource_group_name = azurerm_resource_group.ws.name

  lifecycle { ignore_changes = [tags] }
}


resource "azurerm_subnet_network_security_group_association" "services" {
  network_security_group_id = azurerm_network_security_group.ws.id
  subnet_id                 = azurerm_subnet.services.id
}

resource "azurerm_subnet_network_security_group_association" "webapps" {
  network_security_group_id = azurerm_network_security_group.ws.id
  subnet_id                 = azurerm_subnet.webapps.id
}

resource "azurerm_network_security_rule" "deny-outbound-override" {
  access                      = "Deny"
  destination_address_prefix  = "*"
  destination_port_range      = "*"
  direction                   = "Outbound"
  name                        = "deny-outbound-override"
  network_security_group_name = azurerm_network_security_group.ws.name
  priority                    = 4096
  protocol                    = "*"
  resource_group_name         = azurerm_resource_group.ws.name
  source_address_prefix       = "*"
  source_port_range           = "*"
}

resource "azurerm_network_security_rule" "deny-all-inbound-override" {
  access                      = "Deny"
  destination_address_prefix  = "*"
  destination_port_range      = "*"
  direction                   = "Inbound"
  name                        = "deny-inbound-override"
  network_security_group_name = azurerm_network_security_group.ws.name
  priority                    = 900
  protocol                    = "*"
  resource_group_name         = azurerm_resource_group.ws.name
  source_address_prefix       = "*"
  source_port_range           = "*"
}

resource "azurerm_network_security_rule" "allow-inbound-within-services-subnet" {
  access                      = "Allow"
  destination_port_range      = "*"
  destination_address_prefix  = azurerm_subnet.services.address_prefix
  source_address_prefix       = azurerm_subnet.services.address_prefix
  direction                   = "Inbound"
  name                        = "inbound-within-services-subnet"
  network_security_group_name = azurerm_network_security_group.ws.name
  priority                    = 100
  protocol                    = "*"
  resource_group_name         = azurerm_resource_group.ws.name
  source_port_range           = "*"
}

resource "azurerm_network_security_rule" "allow-outbound-within-services-subnet" {
  access                      = "Allow"
  destination_port_range      = "*"
  destination_address_prefix  = azurerm_subnet.services.address_prefix
  source_address_prefix       = azurerm_subnet.services.address_prefix
  direction                   = "Outbound"
  name                        = "outbound-within-services-subnet"
  network_security_group_name = azurerm_network_security_group.ws.name
  priority                    = 100
  protocol                    = "*"
  resource_group_name         = azurerm_resource_group.ws.name
  source_port_range           = "*"
}

resource "azurerm_network_security_rule" "allow-outbound-to-shared-services" {
  access                      = "Allow"
  destination_address_prefix  = data.azurerm_subnet.shared.address_prefix
  destination_port_range      = "*"
  direction                   = "Outbound"
  name                        = "to-shared-services"
  network_security_group_name = azurerm_network_security_group.ws.name
  priority                    = 110
  protocol                    = "*"
  resource_group_name         = azurerm_resource_group.ws.name
  source_address_prefix       = "*"
  source_port_range           = "*"
}


resource "azurerm_network_security_rule" "allow-outbound-to-internet" {
  access                      = "Allow"
  destination_address_prefix  = "INTERNET"
  destination_port_range      = "443"
  direction                   = "Outbound"
  name                        = "to-internet"
  network_security_group_name = azurerm_network_security_group.ws.name
  priority                    = 120
  protocol                    = "Tcp"
  resource_group_name         = azurerm_resource_group.ws.name
  source_address_prefix       = "*"
  source_port_range           = "*"
}


resource "azurerm_network_security_rule" "allow-outbound-from-webapp-to-core-webapp" {
  access                      = "Allow"
  destination_port_range      = "443"
  destination_address_prefix  = data.azurerm_subnet.core_webapps.address_prefix
  source_address_prefix       = azurerm_subnet.webapps.address_prefix
  direction                   = "Outbound"
  name                        = "outbound-workspace-webapps-to-tre-core-webapps"
  network_security_group_name = azurerm_network_security_group.ws.name
  priority                    = 130
  protocol                    = "TCP"
  resource_group_name         = azurerm_resource_group.ws.name
  source_port_range           = "*"
}

resource "azurerm_network_security_rule" "allow-outbound-webapps-to-services" {
  access = "Allow"
  destination_port_ranges = [
    "80",
    "443",
    "445",
    "3306",
    "3389",
    "5432",
  ]
  destination_address_prefix  = azurerm_subnet.services.address_prefix
  source_address_prefix       = azurerm_subnet.webapps.address_prefix
  direction                   = "Outbound"
  name                        = "outbound-from-services-to-webapps-subnets"
  network_security_group_name = azurerm_network_security_group.ws.name
  priority                    = 140
  protocol                    = "TCP"
  resource_group_name         = azurerm_resource_group.ws.name
  source_port_range           = "*"
}

resource "azurerm_network_security_rule" "allow-inbound-from-bastion" {
  access                       = "Allow"
  destination_address_prefixes = azurerm_subnet.services.address_prefixes
  destination_port_ranges = [
    "22",
    "3389",
  ]
  direction                   = "Inbound"
  name                        = "allow-inbound-from-bastion"
  network_security_group_name = azurerm_network_security_group.ws.name
  priority                    = 110
  protocol                    = "Tcp"
  resource_group_name         = azurerm_resource_group.ws.name
  source_address_prefixes = [
    data.azurerm_subnet.bastion.address_prefix
  ]
  source_port_range = "*"
}

resource "azurerm_network_security_rule" "allow-inbound-from-resourceprocessor" {
  access                       = "Allow"
  destination_address_prefixes = azurerm_subnet.services.address_prefixes
  destination_port_range       = "443"
  direction                    = "Inbound"
  name                         = "allow-inbound-from-resourceprocessor"
  network_security_group_name  = azurerm_network_security_group.ws.name
  priority                     = 120
  protocol                     = "Tcp"
  resource_group_name          = azurerm_resource_group.ws.name
  source_address_prefixes = [
    data.azurerm_subnet.resourceprocessor.address_prefix
  ]
  source_port_range = "*"
}

resource "azurerm_network_security_rule" "allow-inbound-from-webapp-to-services" {
  access = "Allow"
  destination_port_ranges = [
    "80",
    "443",
    "445",
    "3306",
    "3389",
    "5432",
  ]
  destination_address_prefix  = azurerm_subnet.services.address_prefix
  source_address_prefix       = azurerm_subnet.webapps.address_prefix
  direction                   = "Inbound"
  name                        = "inbound-from-webapps-to-services-subnets"
  network_security_group_name = azurerm_network_security_group.ws.name
  priority                    = 130
  protocol                    = "TCP"
  resource_group_name         = azurerm_resource_group.ws.name
  source_port_range           = "*"
}

data "azurerm_route_table" "rt" {
  name                = "rt-${var.tre_id}"
  resource_group_name = local.core_resource_group_name
}

resource "azurerm_subnet_route_table_association" "rt_services_subnet_association" {
  route_table_id = data.azurerm_route_table.rt.id
  subnet_id      = azurerm_subnet.services.id
}

resource "azurerm_subnet_route_table_association" "rt_webapps_subnet_association" {
  route_table_id = data.azurerm_route_table.rt.id
  subnet_id      = azurerm_subnet.webapps.id
}

data "azurerm_private_dns_zone" "azurewebsites" {
  name                = "privatelink.azurewebsites.net"
  resource_group_name = local.core_resource_group_name
}

resource "azurerm_private_dns_zone_virtual_network_link" "azurewebsites" {
  resource_group_name   = local.core_resource_group_name
  virtual_network_id    = azurerm_virtual_network.ws.id
  private_dns_zone_name = data.azurerm_private_dns_zone.azurewebsites.name

  name                 = "azurewebsites-link-${azurerm_virtual_network.ws.name}"
  registration_enabled = false

  lifecycle { ignore_changes = [tags] }
}

data "azurerm_private_dns_zone" "filecore" {
  name                = "privatelink.file.core.windows.net"
  resource_group_name = local.core_resource_group_name

}

resource "azurerm_private_dns_zone_virtual_network_link" "filecorelink" {
  name                  = "filecorelink-${local.workspace_resource_name_suffix}"
  resource_group_name   = local.core_resource_group_name
  private_dns_zone_name = data.azurerm_private_dns_zone.filecore.name
  virtual_network_id    = azurerm_virtual_network.ws.id

  lifecycle { ignore_changes = [tags] }
}


data "azurerm_private_dns_zone" "blobcore" {
  name                = "privatelink.blob.core.windows.net"
  resource_group_name = local.core_resource_group_name

}

resource "azurerm_private_dns_zone_virtual_network_link" "blobcorelink" {
  name                  = "blobcorelink-${local.workspace_resource_name_suffix}"
  resource_group_name   = local.core_resource_group_name
  private_dns_zone_name = data.azurerm_private_dns_zone.blobcore.name
  virtual_network_id    = azurerm_virtual_network.ws.id

  lifecycle { ignore_changes = [tags] }
}

data "azurerm_private_dns_zone" "vaultcore" {
  name                = "privatelink.vaultcore.azure.net"
  resource_group_name = local.core_resource_group_name
}

resource "azurerm_private_dns_zone_virtual_network_link" "vaultcorelink" {
  name                  = "vaultcorelink-${local.workspace_resource_name_suffix}"
  resource_group_name   = local.core_resource_group_name
  private_dns_zone_name = data.azurerm_private_dns_zone.vaultcore.name
  virtual_network_id    = azurerm_virtual_network.ws.id

  lifecycle { ignore_changes = [tags] }
}


data "azurerm_private_dns_zone" "azurecr" {
  name                = "privatelink.azurecr.io"
  resource_group_name = local.core_resource_group_name
}

resource "azurerm_private_dns_zone_virtual_network_link" "azurecrlink" {
  name                  = "azurecrlink-${local.workspace_resource_name_suffix}"
  resource_group_name   = local.core_resource_group_name
  private_dns_zone_name = data.azurerm_private_dns_zone.azurecr.name
  virtual_network_id    = azurerm_virtual_network.ws.id

  lifecycle { ignore_changes = [tags] }
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

resource "azurerm_private_dns_zone_virtual_network_link" "azuremllink" {
  name                  = "azuremllink-${local.workspace_resource_name_suffix}"
  resource_group_name   = local.core_resource_group_name
  private_dns_zone_name = data.azurerm_private_dns_zone.azureml.name
  virtual_network_id    = azurerm_virtual_network.ws.id

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "azuremlcertlink" {
  name                  = "azuremlcertlink-${local.workspace_resource_name_suffix}"
  resource_group_name   = local.core_resource_group_name
  private_dns_zone_name = data.azurerm_private_dns_zone.azuremlcert.name
  virtual_network_id    = azurerm_virtual_network.ws.id

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "notebookslink" {
  name                  = "notebookslink-${local.workspace_resource_name_suffix}"
  resource_group_name   = local.core_resource_group_name
  private_dns_zone_name = data.azurerm_private_dns_zone.notebooks.name
  virtual_network_id    = azurerm_virtual_network.ws.id

  lifecycle { ignore_changes = [tags] }
}

data "azurerm_private_dns_zone" "mysql" {
  name                = "privatelink.mysql.database.azure.com"
  resource_group_name = local.core_resource_group_name

}

resource "azurerm_private_dns_zone_virtual_network_link" "mysqllink" {
  name                  = "mysqllink-${local.workspace_resource_name_suffix}"
  resource_group_name   = local.core_resource_group_name
  private_dns_zone_name = data.azurerm_private_dns_zone.mysql.name
  virtual_network_id    = azurerm_virtual_network.ws.id

  lifecycle { ignore_changes = [tags] }
}

data "azurerm_private_dns_zone" "postgres" {
  name                = "privatelink.postgres.database.azure.com"
  resource_group_name = local.core_resource_group_name

}

resource "azurerm_private_dns_zone_virtual_network_link" "postgreslink" {
  name                  = "postgreslink-${local.workspace_resource_name_suffix}"
  resource_group_name   = local.core_resource_group_name
  private_dns_zone_name = data.azurerm_private_dns_zone.postgres.name
  virtual_network_id    = azurerm_virtual_network.ws.id

  lifecycle { ignore_changes = [tags] }
}
