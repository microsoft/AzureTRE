data "http" "firewall_workbook_json" {
  url = "https://raw.githubusercontent.com/Azure/Azure-Network-Security/master/Azure%20Firewall/Workbook%20-%20Azure%20Firewall%20Monitor%20Workbook/Azure%20Firewall_Gallery.json"
}

resource "random_uuid" "firewall_workbook" {
}

resource "azurerm_application_insights_workbook" "firewall" {
  name                = random_uuid.firewall_workbook.result
  location            = azurerm_resource_group.core.location
  resource_group_name = azurerm_resource_group.core.name
  display_name        = "Azure Firewall Workbook ${var.tre_id}"
  data_json           = data.http.firewall_workbook_json.response_body
  tags                = local.tre_core_tags
}
