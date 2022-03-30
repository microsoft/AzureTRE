resource "azurerm_public_ip" "fwpip" {
  name                = "pip-fw-${var.tre_id}"
  resource_group_name = local.core_resource_group_name
  location            = data.azurerm_resource_group.rg.location
  allocation_method   = "Static"
  sku                 = "Standard"

  lifecycle { ignore_changes = [tags] }
}

// Note: No Azure Firewall Manager policy charges will be done for policies that are associated to a single firewall.
// (see https://azure.microsoft.com/en-gb/pricing/details/firewall-manager/)
resource "azurerm_firewall_policy" "fw_policy" {
  name                = "fwpolicy-${var.tre_id}"
  resource_group_name = local.core_resource_group_name
  location            = data.azurerm_resource_group.rg.location
}

resource "azurerm_firewall_policy_rule_collection_group" "rule_collection_group" {
  name               = "fwpolicy-rcg-${var.tre_id}"
  firewall_policy_id = azurerm_firewall_policy.fw_policy.id
  priority           = 500

  network_rule_collection {
    name     = "general"
    priority = 200
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
    name     = "nrc-resource_processor_subnet"
    action   = "Allow"
    priority = 201

    rule {
      name = "AzureServiceTags"

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
      source_addresses = data.azurerm_subnet.resource_processor.address_prefixes
    }
  }

  network_rule_collection {
    name     = "nrc-web_app_subnet"
    priority = 202
    action   = "Allow"

    rule {
      name = "Azure-Services"

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
      source_addresses = data.azurerm_subnet.web_app.address_prefixes
    }
  }

  application_rule_collection {
    name     = "arc-shared_subnet"
    priority = 300
    action   = "Allow"

    rule {
      name = "admin-resources"

      protocols {
        port = "443"
        type = "Https"
      }

      protocols {
        port = "80"
        type = "Http"
      }

      destination_fqdns = [
        "go.microsoft.com",
        "*.azureedge.net",
        "*github.com",
        "*powershellgallery.com",
        "git-scm.com",
        "*githubusercontent.com",
        "*core.windows.net",
        "aka.ms",
        "management.azure.com",
        "graph.microsoft.com",
        "login.microsoftonline.com",
        "aadcdn.msftauth.net",
        "graph.windows.net"
      ]

      source_addresses = data.azurerm_subnet.shared.address_prefixes
    }
  }

  application_rule_collection {
    name     = "arc-resource_processor_subnet"
    priority = 301
    action   = "Allow"

    rule {
      name = "package-sources"

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
        "download.docker.com",
        "registry-1.docker.io",
        "auth.docker.io",
        "registry.terraform.io",
        "releases.hashicorp.com"
      ]
      source_addresses = data.azurerm_subnet.resource_processor.address_prefixes
    }
  }

  application_rule_collection {
    name     = "arc-web_app_subnet"
    priority = 302
    action   = "Allow"
    rule {
      name = "microsoft-graph"
      protocols {
        port = "443"
        type = "Https"
      }

      destination_fqdns = [
        "graph.microsoft.com"
      ]
      source_addresses = data.azurerm_subnet.web_app.address_prefixes
    }
  }
}

resource "azurerm_firewall" "fw" {
  depends_on          = [azurerm_public_ip.fwpip]
  name                = "fw-${var.tre_id}"
  resource_group_name = local.core_resource_group_name
  location            = data.azurerm_resource_group.rg.location
  firewall_policy_id  = azurerm_firewall_policy.fw_policy.id
  ip_configuration {
    name                 = "fw-ip-configuration"
    subnet_id            = data.azurerm_subnet.firewall.id
    public_ip_address_id = azurerm_public_ip.fwpip.id
  }

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_management_lock" "fw" {
  count      = var.stateful_resources_locked ? 1 : 0
  name       = azurerm_firewall.fw.name
  scope      = azurerm_firewall.fw.id
  lock_level = "CanNotDelete"
  notes      = "Locked to prevent accidental deletion"
}

resource "azurerm_monitor_diagnostic_setting" "firewall" {
  name                           = "diagnostics-firewall-${var.tre_id}"
  target_resource_id             = azurerm_firewall.fw.id
  log_analytics_workspace_id     = data.azurerm_log_analytics_workspace.tre.id
  log_analytics_destination_type = "Dedicated"

  log {
    category = "AzureFirewallApplicationRule"
    enabled  = true


    retention_policy {
      enabled = false
      days    = 0
    }
  }

  log {

    category = "AzureFirewallNetworkRule"
    enabled  = true

    retention_policy {
      enabled = false
      days    = 0
    }
  }
  log {

    category = "AzureFirewallDnsProxy"
    enabled  = true

    retention_policy {
      enabled = false
      days    = 0
    }
  }
  log {

    category = "AzureFirewallNetworkRule"
    enabled  = true

    retention_policy {
      enabled = false
      days    = 0
    }
  }

  metric {
    category = "AllMetrics"
    enabled  = true

    retention_policy {
      enabled = false
      days    = 0
    }
  }
}
