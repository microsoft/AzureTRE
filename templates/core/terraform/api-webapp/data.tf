data "local_file" "version" {
  filename = "${path.module}/../../../../api_app/_version.py"
}

data "azurerm_container_registry" "mgmt_acr" {
  name                = var.mgmt_acr_name
  resource_group_name = var.mgmt_resource_group_name
}
