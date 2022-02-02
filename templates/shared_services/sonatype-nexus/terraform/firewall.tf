resource "azurerm_firewall_application_rule_collection" "web_app_subnet_nexus" {
  name                = "arc-web_app_subnet_nexus"
  azure_firewall_name = data.azurerm_firewall.fw.name
  resource_group_name = data.azurerm_firewall.fw.resource_group_name
  priority            = 104
  action              = "Allow"

  rule {
    name = "nexus-package-sources"
    protocol {
      port = "443"
      type = "Https"
    }
    protocol {
      port = "80"
      type = "Http"
    }

    target_fqdns     = local.nexus_allowed_fqdns_list
    source_addresses = data.azurerm_subnet.web_app.address_prefixes
  }
}
