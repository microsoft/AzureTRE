resource "azurerm_public_ip" "fwtransit" {
  count               = var.firewall_force_tunnel_ip != "" ? 0 : 1
  name                = "pip-fw-${var.tre_id}"
  resource_group_name = local.core_resource_group_name
  location            = data.azurerm_resource_group.rg.location
  allocation_method   = "Static"
  sku                 = "Standard"
  tags                = local.tre_shared_service_tags

  lifecycle { ignore_changes = [tags, zones] }
}

moved {
  from = azurerm_public_ip.fwpip
  to   = azurerm_public_ip.fwtransit[0]
}

resource "azurerm_public_ip" "fwmanagement" {
  count               = (var.firewall_force_tunnel_ip != "" || local.effective_firewall_sku == "Basic") ? 1 : 0
  name                = "pip-fw-management-${var.tre_id}"
  resource_group_name = local.core_resource_group_name
  location            = data.azurerm_resource_group.rg.location
  allocation_method   = "Static"
  sku                 = "Standard"
  tags                = local.tre_shared_service_tags

  lifecycle { ignore_changes = [tags, zones] }
}


resource "azurerm_firewall" "fw" {
  name                = local.firewall_name
  resource_group_name = local.core_resource_group_name
  location            = data.azurerm_resource_group.rg.location
  sku_tier            = local.effective_firewall_sku
  sku_name            = "AZFW_VNet"
  firewall_policy_id  = azurerm_firewall_policy.root.id
  tags                = local.tre_shared_service_tags
  ip_configuration {
    name                 = "fw-ip-configuration"
    subnet_id            = data.azurerm_subnet.firewall.id
    public_ip_address_id = var.firewall_force_tunnel_ip != "" ? null : azurerm_public_ip.fwtransit[0].id
  }

  dynamic "management_ip_configuration" {
    for_each = (var.firewall_force_tunnel_ip != "" || local.effective_firewall_sku == "Basic") ? [1] : []
    content {
      name                 = "mgmtconfig"
      subnet_id            = data.azurerm_subnet.firewall_management.id
      public_ip_address_id = azurerm_public_ip.fwmanagement[0].id
    }
  }

  lifecycle { ignore_changes = [tags] }
}

data "azurerm_monitor_diagnostic_categories" "firewall" {
  resource_id = azurerm_firewall.fw.id
}

resource "azurerm_monitor_diagnostic_setting" "firewall" {
  name                           = "diagnostics-fw-${var.tre_id}"
  target_resource_id             = azurerm_firewall.fw.id
  log_analytics_workspace_id     = data.azurerm_log_analytics_workspace.tre.id
  log_analytics_destination_type = "Dedicated"

  dynamic "enabled_log" {
    for_each = setintersection(data.azurerm_monitor_diagnostic_categories.firewall.log_category_types, local.firewall_diagnostic_categories_enabled)
    content {
      category = enabled_log.value
    }
  }

  metric {
    category = "AllMetrics"
    enabled  = true
  }
}

resource "azurerm_firewall_policy" "root" {
  name                = local.firewall_policy_name
  resource_group_name = local.core_resource_group_name
  location            = data.azurerm_resource_group.rg.location
  sku                 = local.effective_firewall_sku
  tags                = local.tre_shared_service_tags

  lifecycle { ignore_changes = [tags] }
}
