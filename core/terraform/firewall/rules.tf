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

        // Needed when a workspace key vault is created before its private endpoint
        "AzureKeyVault.${var.location}"
      ]
      destination_ports = [
        "443"
      ]
      source_ip_groups = [var.resource_processor_ip_group_id]
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
        "AzureResourceManager"
      ]
      destination_ports = [
        "443"
      ]
      source_ip_groups = [var.web_app_ip_group_id]
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
      source_ip_groups = [var.resource_processor_ip_group_id]
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
      source_ip_groups = [var.resource_processor_ip_group_id]
    }
    # This rule is needed to support Gov Cloud.
    # The az cli uses msal lib which requires access to this fqdn for authentication.
    rule {
      name = "microsoft-login"
      protocols {
        port = "443"
        type = "Https"
      }
      destination_fqdns = [
        "login.microsoftonline.com",
      ]
      source_ip_groups = [var.resource_processor_ip_group_id]
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
      source_ip_groups = [var.shared_services_ip_group_id]
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
      source_ip_groups = [var.web_app_ip_group_id]
    }
  }

  application_rule_collection {
    name     = "arc-airlock-processor-subnet"
    priority = 304
    action   = "Allow"

    rule {
      name = "functions-runtime"
      protocols {
        port = "443"
        type = "Https"
      }
      destination_fqdns = [
        "functionscdn.azureedge.net"
      ]
      source_ip_groups = [var.airlock_processor_ip_group_id]
    }
  }

  depends_on = [
    azurerm_firewall.fw
  ]
}
