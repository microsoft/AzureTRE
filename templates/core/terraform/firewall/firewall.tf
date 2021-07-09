resource "azurerm_public_ip" "fwpip" {
  name                = "pip-fw-${var.tre_id}"
  resource_group_name = var.resource_group_name
  location            = var.location
  allocation_method   = "Static"
  sku                 = "Standard"

  lifecycle { ignore_changes = [ tags ] }
}

resource "azurerm_firewall" "fw" {
  depends_on          = [azurerm_public_ip.fwpip]
  name                = "fw-${var.tre_id}"
  resource_group_name = var.resource_group_name
  location            = var.location
  ip_configuration {
    name                 = "fw-ip-configuration"
    subnet_id            = var.firewall_subnet
    public_ip_address_id = azurerm_public_ip.fwpip.id
  }

  lifecycle { ignore_changes = [ tags ] }
}

resource "azurerm_monitor_diagnostic_setting" "firewall" {
  name                       = "diagnostics-firewall-${var.tre_id}"
  target_resource_id         = azurerm_firewall.fw.id
  log_analytics_workspace_id = var.log_analytics_workspace_id
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
