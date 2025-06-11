data "azurerm_ip_group" "referenced" {
  for_each = toset(distinct(flatten(
    [for collection in concat(local.api_driven_network_rule_collection, local.api_driven_application_rule_collection) :
      [for rule in collection.rules : try(rule.source_ip_groups_in_core, [])]
    ]
  )))
  name                = each.value
  resource_group_name = local.core_resource_group_name
}
