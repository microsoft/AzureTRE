resource "azurerm_firewall_application_rule_collection" "shared_subnet_sonatype_nexus" {
  name                = "shared_subnet_sonatype_nexus"
  azure_firewall_name = data.azurerm_firewall.fw.name
  resource_group_name = data.azurerm_firewall.fw.resource_group_name
  priority            = 105
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
    source_addresses = data.azurerm_subnet.shared.address_prefixes
  }

  rule {
    name = "windows-vm-crl"
    protocol {
      port = "443"
      type = "Https"
    }
    protocol {
      port = "80"
      type = "Http"
    }

    target_fqdns = local.workspace_vm_allowed_fqdns_list
    source_addresses = data.azurerm_subnet.services.address_prefixes
  }
}
