resource "azurerm_firewall_policy_rule_collection_group" "core_airlock_notifier" {
  name               = "rcg-core-airlock-notifier"
  firewall_policy_id = data.azurerm_firewall_policy.core.id
  priority           = 501

  network_rule_collection {
    name     = "nrc-resource-processor-appservice-deployment"
    priority = 201
    action   = "Allow"

    rule {
      name = "AppService"
      protocols = [
        "TCP"
      ]
      destination_addresses = [
        "AppService",
        "AzureConnectors",
        "LogicApps",
        "LogicAppsManagement"
      ]
      destination_ports = [
        "443"
      ]
      source_ip_groups = [data.azurerm_ip_group.resource_processor.id]
    }
  }
}
