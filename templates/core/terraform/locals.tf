data "azurerm_subscription" "current" {}

data "azurerm_client_config" "current" {}

# Random unique id
resource "random_string" "unique_id" {
  length      = 4
  min_numeric = 4
}

data "azurerm_container_registry" "mgmt_acr" {
  name                = var.acr_name
  resource_group_name = var.mgmt_resource_group_name
}

data "http" "myip" {
  count = var.local_ip_address == ""
  url   = "https://ipecho.net/plain"
}

locals {
  myip = var.local_ip_address != "" ? var.local_ip_address : chomp(data.http.myip.body)
}
