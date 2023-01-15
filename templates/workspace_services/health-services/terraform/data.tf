data "azurerm_resource_group" "ws" {
  name = "rg-${var.tre_id}-ws-${local.short_workspace_id}"
}

data "azurerm_virtual_network" "ws" {
  name                = "vnet-${var.tre_id}-ws-${local.short_workspace_id}"
  resource_group_name = "rg-${var.tre_id}-ws-${local.short_workspace_id}"
}

data "azurerm_key_vault" "ws" {
  name                = local.keyvault_name
  resource_group_name = data.azurerm_resource_group.ws.name
}

data "azurerm_key_vault_secret" "aad_tenant_id" {
  name         = "auth-tenant-id"
  key_vault_id = data.azurerm_key_vault.ws.id
}

data "azurerm_firewall" "fw" {
  name                = "fw-${var.tre_id}"
  resource_group_name = data.azurerm_resource_group.rg.name
}

data "external" "rule_priorities" {
  program = ["bash", "-c", "./get_firewall_priorities.sh"]

  query = {
    firewall_name          = data.azurerm_firewall.fw.name
    resource_group_name    = data.azurerm_firewall.fw.resource_group_name
    collection_name_suffix = "${local.service_resource_name_suffix}-aml"
  }
  depends_on = [
    null_resource.az_login_sp,
    null_resource.az_login_msi
  ]
}

data "azurerm_subnet" "services" {
  name                 = "ServicesSubnet"
  virtual_network_name = data.azurerm_virtual_network.ws.name
  resource_group_name  = data.azurerm_resource_group.ws.name
}

data "azurerm_private_dns_zone" "health" {
  name                = "privatelink.azurehealthcareapis.com"
  resource_group_name = local.core_resource_group_name
}

data "azurerm_private_dns_zone" "dicom" {
  name                = "privatelink.dicom.azurehealthcareapis.com"
  resource_group_name = local.core_resource_group_name
}
