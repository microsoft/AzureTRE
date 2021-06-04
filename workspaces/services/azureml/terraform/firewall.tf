# TODO: Remove when have shared services support

data "azurerm_firewall" "fw" {
  name                = "fw-${var.tre_id}"
  resource_group_name = "rg-${var.tre_id}"
}


resource "azurerm_firewall_network_rule_collection" "networkrulecollection" {
  name                = "networkrulecollection-${local.service_resource_name_suffix}"
  azure_firewall_name = data.azurerm_firewall.fw.name
  resource_group_name = data.azurerm_firewall.fw.resource_group_name
  priority            = tonumber("1${local.service_id}")
  action              = "Allow"

  rule {
    name = "allowStorage"

    source_addresses = data.azurerm_virtual_network.ws.address_space


    destination_ports = [
      "*"
    ]

    destination_addresses = local.allowed_service_tags

    protocols = [
      "TCP"
    ]
  }
}

resource "azurerm_firewall_application_rule_collection" "apprulecollection" {
  name                = "apprulecollection-${local.service_resource_name_suffix}"
  azure_firewall_name = data.azurerm_firewall.fw.name
  resource_group_name = data.azurerm_firewall.fw.resource_group_name
  priority            = tonumber("2${local.service_id}")
  action              = "Allow"

  rule {
    name = "allowMLrelated"

    source_addresses = data.azurerm_virtual_network.ws.address_space


    target_fqdns = local.allowed_urls

    protocol {
      port = "443"
      type = "Https"
    }
    protocol {
      port = "80"
      type = "Http"
    }
  }
}
