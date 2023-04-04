resource "azurerm_firewall_policy_rule_collection_group" "core" {
  name               = "rcg-core"
  firewall_policy_id = azurerm_firewall_policy.root.id
  priority           = 500

  network_rule_collection {
    name     = "nrc-general"
    priority = 201
    action   = "Allow"

    rule {
      name = "time"
      protocols = [
        "UDP"
      ]
      destination_addresses = [
        "*"
      ]
      destination_ports = [
        "123"
      ]
      source_addresses = [
        "*"
      ]
    }
  }

  network_rule_collection {
    name     = "nrc-resource-processor-subnet"
    priority = 202
    action   = "Allow"

    rule {
      name = "azure-services"
      protocols = [
        "TCP"
      ]
      destination_addresses = [
        "AzureActiveDirectory",
        "AzureResourceManager",
        "AzureContainerRegistry",
        "Storage",
        "AzureKeyVault"
      ]
      destination_ports = [
        "443"
      ]
      source_ip_groups = [data.azurerm_ip_group.resource_processor.id]
    }
  }

  network_rule_collection {
    name     = "nrc-web-app-subnet"
    priority = 203
    action   = "Allow"

    rule {
      name = "azure-services"
      protocols = [
        "TCP"
      ]
      destination_addresses = [
        "AzureActiveDirectory",
        "AzureContainerRegistry",
        "AzureResourceManager"
      ]
      destination_ports = [
        "443"
      ]
      source_ip_groups = [data.azurerm_ip_group.web.id]
    }
  }

  application_rule_collection {
    name     = "arc-resource-processor-subnet"
    priority = 301
    action   = "Allow"

    rule {
      name = "os-package-sources"
      protocols {
        port = "443"
        type = "Https"
      }
      protocols {
        port = "80"
        type = "Http"
      }
      destination_fqdns = [
        "packages.microsoft.com",
        "keyserver.ubuntu.com",
        "api.snapcraft.io",
        "azure.archive.ubuntu.com",
        "security.ubuntu.com",
        "entropy.ubuntu.com",
      ]
      source_ip_groups = [data.azurerm_ip_group.resource_processor.id]
    }

    rule {
      name = "docker-sources"
      protocols {
        port = "443"
        type = "Https"
      }
      protocols {
        port = "80"
        type = "Http"
      }
      destination_fqdns = [
        "download.docker.com",
        "registry-1.docker.io",
        "auth.docker.io",
      ]
      source_ip_groups = [data.azurerm_ip_group.resource_processor.id]
    }
  }

  application_rule_collection {
    name     = "arc-shared-subnet"
    priority = 302
    action   = "Allow"

    rule {
      name = "nexus-bootstrap"
      protocols {
        port = "443"
        type = "Https"
      }
      protocols {
        port = "80"
        type = "Http"
      }
      destination_fqdns = [
        "keyserver.ubuntu.com",
        "packages.microsoft.com",
        "download.docker.com",
        "azure.archive.ubuntu.com"
      ]
      source_ip_groups = [data.azurerm_ip_group.shared.id]
    }
  }

  application_rule_collection {
    name     = "arc-web-app-subnet"
    priority = 303
    action   = "Allow"

    rule {
      name = "microsoft-graph"
      protocols {
        port = "443"
        type = "Https"
      }
      destination_fqdns = [
        var.microsoft_graph_fqdn
      ]
      source_ip_groups = [data.azurerm_ip_group.web.id]
    }
  }
}


resource "azurerm_firewall_policy_rule_collection_group" "dynamic_network" {
  name               = "rcg-dynamic-network"
  firewall_policy_id = azurerm_firewall_policy.root.id
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

  depends_on = [
    azurerm_firewall_policy_rule_collection_group.core
  ]
}

resource "azurerm_firewall_policy_rule_collection_group" "dynamic_application" {
  name               = "rcg-dynamic-application"
  firewall_policy_id = azurerm_firewall_policy.root.id
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
