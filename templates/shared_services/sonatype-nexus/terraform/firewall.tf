resource "azurerm_firewall_policy_rule_collection_group" "nexus_rule_collection_group" {
  name               = "fwpolicy-rcg-${var.tre_id}-nexus"
  firewall_policy_id = data.azurerm_firewall_policy.fw_policy.id
  priority           = 501

  application_rule_collection {
    name     = "arc-web_app_subnet_nexus"
    priority = 304
    action   = "Allow"

    rule {
      name = "nexus-package-sources"
      protocols {
        port = "443"
        type = "Https"
      }
      protocols {
        port = "80"
        type = "Http"
      }

      destination_fqdns = local.nexus_allowed_fqdns_list
      source_addresses  = data.azurerm_subnet.web_app.address_prefixes
    }
  }
}
