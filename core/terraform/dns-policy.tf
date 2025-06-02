resource "azapi_resource" "dnspolicy" {
  count     = var.enable_dns_policy ? 1 : 0
  type      = "Microsoft.Network/dnsResolverPolicies@${local.dns_policy_azapi_ver}"
  parent_id = azurerm_resource_group.core.id
  name      = "dnspol-${var.tre_id}"
  location  = var.location

  body = {
    properties = {

    }
  }
}

resource "azapi_resource" "domain_list_allow" {
  count     = var.enable_dns_policy ? local.dns_policy_num_rules : 0
  type      = "Microsoft.Network/dnsResolverDomainLists@${local.dns_policy_azapi_ver}"
  parent_id = azurerm_resource_group.core.id
  name      = "dl-allowed-${count.index + 1}"
  location  = var.location
  body = {
    properties = {
      domains : slice(local.dns_policy_allowed_domains, count.index * 100, min((count.index * 100) + 100, length(local.dns_policy_allowed_domains)))
    }
  }
}

resource "azapi_resource" "domain_list_all" {
  count     = var.enable_dns_policy ? 1 : 0
  type      = "Microsoft.Network/dnsResolverDomainLists@${local.dns_policy_azapi_ver}"
  parent_id = azurerm_resource_group.core.id
  name      = "dl-all"
  location  = var.location
  body = {
    properties = {
      domains : ["."]
    }
  }
}

resource "azapi_resource" "allow_rule" {
  count     = var.enable_dns_policy ? 1 : 0
  type      = "Microsoft.Network/dnsResolverPolicies/dnsSecurityRules@${local.dns_policy_azapi_ver}"
  parent_id = azapi_resource.dnspolicy[0].id
  name      = "allow"
  location  = var.location

  body = {
    properties = {
      priority = 100
      action = {
        actionType = "Allow"
      }
      dnsResolverDomainLists = [for i in range(local.dns_policy_num_rules) : { id = azapi_resource.domain_list_allow[i].id }]
      dnsSecurityRuleState   = "Enabled"
    }
  }
}


resource "azapi_resource" "deny_rule" {
  count     = var.enable_dns_policy ? 1 : 0
  type      = "Microsoft.Network/dnsResolverPolicies/dnsSecurityRules@${local.dns_policy_azapi_ver}"
  parent_id = azapi_resource.dnspolicy[0].id
  name      = "deny"
  location  = var.location

  body = {
    properties = {
      priority = 65000
      action = {
        actionType = "Block"
      }
      dnsResolverDomainLists = [
        {
          id = azapi_resource.domain_list_all[0].id
        }
      ]
      dnsSecurityRuleState = "Enabled"
    }
  }
}

resource "azapi_resource" "core_vnet_link" {
  count     = var.enable_dns_policy ? 1 : 0
  type      = "Microsoft.Network/dnsResolverPolicies/virtualNetworkLinks@${local.dns_policy_azapi_ver}"
  parent_id = azapi_resource.dnspolicy[0].id
  name      = "core"
  location  = var.location
  body = {
    properties = {
      virtualNetwork = {
        id = module.network.core_vnet_id
      }
    }
  }
}

resource "azurerm_monitor_diagnostic_setting" "dns_policy" {
  count                      = var.enable_dns_policy ? 1 : 0
  name                       = "diagnostics"
  target_resource_id         = azapi_resource.dnspolicy[0].id
  log_analytics_workspace_id = module.azure_monitor.log_analytics_workspace_id
  enabled_log {
    category = "DnsResponse"
  }
  metric {
    category = "AllMetrics"
    enabled  = false
  }
}
