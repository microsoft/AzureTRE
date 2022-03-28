data "local_file" "version" {
  filename = "${path.module}/../../../../../resource_processor/version.txt"
}

data "azurerm_user_assigned_identity" "resource_processor_vmss_id" {
  name                = "id-vmss-${var.tre_id}"
  resource_group_name = "rg-${var.tre_id}"
}
