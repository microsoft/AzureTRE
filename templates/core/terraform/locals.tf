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
  count = var.public_deployment_ip_address == "" ? 1 : 0
  url   = "https://ipecho.net/plain"
}

locals {
  myip = var.public_deployment_ip_address != "" ? var.public_deployment_ip_address : chomp(data.http.myip[0].body)
}
