resource "azurerm_firewall_application_rule_collection" "web_app_subnet_gitea" {
  name                = "arc-web_app_subnet_gitea"
  azure_firewall_name = var.firewall_name
  resource_group_name = var.firewall_resource_group_name
  priority            = 103
  action              = "Allow"

  rule {
    name = "gitea-sources"
    protocol {
      port = "443"
      type = "Https"
    }
    protocol {
      port = "80"
      type = "Http"
    }

    target_fqdns     = local.gitea_allowed_fqdns_list
    source_addresses = var.web_app_subnet_address_prefixes
  }
}
