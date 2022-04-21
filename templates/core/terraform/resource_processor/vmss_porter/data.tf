data "local_file" "version" {
  filename = "${path.module}/../../../../../resource_processor/version.txt"
}

data "azurerm_key_vault" "kv" {
  name                = var.key_vault_name
  resource_group_name = var.resource_group_name
}