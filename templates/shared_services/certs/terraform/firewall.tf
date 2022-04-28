resource "azurerm_firewall_application_rule_collection" "resource_processor_letsencrypt" {
  name                = "resource_processor_subnet_letsencrypt"
  azure_firewall_name = data.azurerm_firewall.fw.name
  resource_group_name = data.azurerm_firewall.fw.resource_group_name
  priority            = 106
  action              = "Allow"

  rule {
    name = "letsencrypt-acme"
    protocol {
      port = "443"
      type = "Https"
    }
    protocol {
      port = "80"
      type = "Http"
    }

    target_fqdns = [
      "acme-v02.api.letsencrypt.org"
    ]

    source_addresses = data.azurerm_subnet.resource_processor.address_prefixes
  }
}
