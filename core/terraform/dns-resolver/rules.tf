data "external" "dns-rules" {
  program = ["bash", "${path.module}/make-rules.sh"]
}

resource "azurerm_private_dns_resolver_forwarding_rule" "dns-rules" {
  # This is how to do it in-situ, in which case you don't need the 'jsondecode' wrappers below
  # for_each = tomap( {
  #       net  = { domain = "net.", address = "8.8.8.8" },
  #       sink = { domain = ".",    address = "0.0.0.0" }
  # } )
  for_each                  = data.external.dns-rules.result
  name                      = "dns-rule-${each.key}"
  dns_forwarding_ruleset_id = azurerm_private_dns_resolver_dns_forwarding_ruleset.dns-ruleset.id
  domain_name               = jsondecode(each.value).domain
  enabled                   = true
  target_dns_servers {
    ip_address = jsondecode(each.value).address
    port       = 53
  }
}
