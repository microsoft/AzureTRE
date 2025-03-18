locals {
  allowedDomains = tolist(jsondecode(file("${path.module}/allowed-dns.json")))
  # Maximum of 100 domains per rule, so split into sub-arrays
  numRules = floor((length(local.allowedDomains) + 100) / 100)
}

resource "azapi_resource" "dnspolicy" {
  type      = "Microsoft.Network/dnsResolverPolicies@2023-07-01-preview"
  parent_id = azurerm_resource_group.core.id
  name      = "dnspol-${var.tre_id}"
  location  = var.location

  body = {
    properties = {

    }
  }
}

resource "azapi_resource" "domain_list_allow" {
  count     = local.numRules
  type      = "Microsoft.Network/dnsResolverDomainLists@2023-07-01-preview"
  parent_id = azurerm_resource_group.core.id
  name      = "dl-allowed-${count.index + 1}"
  location  = var.location
  body = {
    properties = {
      domains : slice(local.allowedDomains, count.index * 100, min((count.index * 100)+100, local.numRules))
    }
  }
}

resource "azapi_resource" "domain_list_all" {
  type      = "Microsoft.Network/dnsResolverDomainLists@2023-07-01-preview"
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
  type      = "Microsoft.Network/dnsResolverPolicies/dnsSecurityRules@2023-07-01-preview"
  parent_id = azapi_resource.dnspolicy.id
  name      = "allow"
  location  = var.location

  body = {
    properties = {
      priority = 100
      action = {
        actionType = "Allow"
      }
      dnsResolverDomainLists = [for i in range(local.numRules) : { id = azapi_resource.domain_list_allow[i].id }]
      dnsSecurityRuleState   = "Enabled"
    }
  }
}


resource "azapi_resource" "deny_rule" {
  type      = "Microsoft.Network/dnsResolverPolicies/dnsSecurityRules@2023-07-01-preview"
  parent_id = azapi_resource.dnspolicy.id
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
          id = azapi_resource.domain_list_all.id
        }
      ]
      dnsSecurityRuleState = "Enabled"
    }
  }
}
