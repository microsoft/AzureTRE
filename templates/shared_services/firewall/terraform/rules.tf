resource "azurerm_firewall_policy_rule_collection_group" "dynamic_network" {
  name               = "rcg-dynamic-network"
  firewall_policy_id = var.firewall_policy_id
  priority           = 510

  dynamic "network_rule_collection" {
    for_each = { for i, v in local.api_driven_network_rule_collection : i => v }

    content {
      name     = network_rule_collection.value.name
      priority = 200 + network_rule_collection.key
      action   = "Allow"

      dynamic "rule" {
        for_each = network_rule_collection.value.rules

        content {
          name = rule.value.name
          # description      = rule.value.description
          source_addresses = try(rule.value.source_addresses, [])
          source_ip_groups = concat(
            try(rule.value.source_ip_group_ids, []),
            try([for item in rule.value.source_ip_groups_in_core : data.azurerm_ip_group.referenced[item].id], [])
          )
          destination_addresses = try(rule.value.destination_addresses, [])
          destination_ip_groups = try(rule.value.destination_ip_group_ids, [])
          destination_fqdns     = try(rule.value.destination_fqdns, [])
          destination_ports     = try(rule.value.destination_ports, [])
          protocols             = try(rule.value.protocols, [])
        }
      }
    }
  }
}

resource "azurerm_firewall_policy_rule_collection_group" "dynamic_application" {
  name               = "rcg-dynamic-application"
  firewall_policy_id = var.firewall_policy_id
  priority           = 520

  dynamic "application_rule_collection" {
    for_each = { for i, v in local.api_driven_application_rule_collection : i => v }

    content {
      name     = application_rule_collection.value.name
      priority = 200 + application_rule_collection.key
      action   = "Allow"

      dynamic "rule" {
        for_each = application_rule_collection.value.rules

        content {
          name        = rule.value.name
          description = rule.value.description

          dynamic "protocols" {
            for_each = rule.value.protocols

            content {
              port = protocols.value.port
              type = protocols.value.type
            }
          }

          destination_fqdns = try(rule.value.target_fqdns, [])
          source_addresses  = try(rule.value.source_addresses, [])
          source_ip_groups = concat(
            try(rule.value.source_ip_group_ids, []),
            try([for item in rule.value.source_ip_groups_in_core : data.azurerm_ip_group.referenced[item].id], [])
          )
          destination_fqdn_tags = try(rule.value.fqdn_tags, [])
        }
      }
    }
  }

  depends_on = [
    azurerm_firewall_policy_rule_collection_group.dynamic_network
  ]
}
