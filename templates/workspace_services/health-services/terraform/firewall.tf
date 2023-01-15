resource "azurerm_firewall_application_rule_collection" "health_services_authentication" {
  name                = "azure_authentication"
  azure_firewall_name = data.azurerm_firewall.fw.name
  resource_group_name = data.azurerm_firewall.fw.resource_group_name
  priority            = data.external.rule_priorities.result.application_rule_priority
  action              = "Allow"

  rule {
    name = "azure-portal-authentication"
    protocol {
      port = "443"
      type = "Https"
    }
    protocol {
      port = "80"
      type = "Http"
    }

    # Taken from the whitelist for Azure portal authentication:
    # https://learn.microsoft.com/en-us/azure/azure-portal/azure-portal-safelist-urls?tabs=public-cloud
    target_fqdns = [
      "*.login.microsoftonline.com",
      "*.aadcdn.msftauth.net",
      "*.aadcdn.msftauthimages.net",
      "*.aadcdn.msauthimages.net",
      "*.logincdn.msftauth.net",
      "*.login.live.com",
      "*.msauth.net",
      "*.aadcdn.microsoftonline-p.com",
      "*.microsoftonline-p.com"
    ]

    source_addresses = data.azurerm_virtual_network.ws.address_space
  }
}
