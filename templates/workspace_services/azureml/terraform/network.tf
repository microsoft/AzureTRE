
data "azurerm_network_security_group" "ws" {
  name                = "nsg-ws"
  resource_group_name = data.azurerm_resource_group.ws.name
}


resource "null_resource" "az_login_sp" {

  count = var.arm_use_msi == true ? 0 : 1
  provisioner "local-exec" {
    command = "az login --service-principal --username ${var.arm_client_id} --password ${var.arm_client_secret} --tenant ${var.arm_tenant_id}"
  }

  triggers = {
    timestamp = timestamp()
  }

}

resource "null_resource" "az_login_msi" {

  count = var.arm_use_msi == true ? 1 : 0
  provisioner "local-exec" {
    command = "az login --identity -u '${data.azurerm_client_config.current.client_id}'"
  }

  triggers = {
    timestamp = timestamp()
  }
}

data "external" "nsg_rule_priorities_inbound" {
  program = ["bash", "-c", "./get_nsg_priorities.sh"]

  query = {
    nsg_name            = data.azurerm_network_security_group.ws.name
    resource_group_name = data.azurerm_resource_group.ws.name
    nsg_rule_name       = "${local.short_service_id}-aml-inbound"
    direction           = "Inbound"
  }
  depends_on = [
    null_resource.az_login_sp,
    null_resource.az_login_msi
  ]
}



data "external" "nsg_rule_priorities_outbound" {
  program = ["bash", "-c", "./get_nsg_priorities.sh"]

  query = {
    nsg_name            = data.azurerm_network_security_group.ws.name
    nsg_rule_name       = "${local.short_service_id}-allow-Outbound_Storage_445"
    resource_group_name = data.azurerm_resource_group.ws.name
    direction           = "Outbound"
  }
  depends_on = [
    null_resource.az_login_sp,
    null_resource.az_login_msi
  ]
}


resource "azurerm_network_security_rule" "allow_aml_inbound" {
  access                      = "Allow"
  destination_port_ranges     = ["29877", "29876", "44224"]
  destination_address_prefix  = "VirtualNetwork"
  source_address_prefix       = "VirtualNetwork"
  direction                   = "Inbound"
  name                        = "${local.short_service_id}-aml-inbound"
  network_security_group_name = data.azurerm_network_security_group.ws.name
  priority                    = tonumber(data.external.nsg_rule_priorities_inbound.result.nsg_rule_priority)
  protocol                    = "Tcp"
  resource_group_name         = data.azurerm_resource_group.ws.name
  source_port_range           = "*"
}


resource "azurerm_network_security_rule" "allow_outbound_storage_445" {
  access                      = "Allow"
  destination_port_range      = "445"
  destination_address_prefix  = "Storage"
  source_address_prefix       = "VirtualNetwork"
  direction                   = "Outbound"
  name                        = "${local.short_service_id}-allow-Outbound_Storage_445"
  network_security_group_name = data.azurerm_network_security_group.ws.name
  priority                    = tonumber(data.external.nsg_rule_priorities_outbound.result.nsg_rule_priority)
  protocol                    = "Tcp"
  resource_group_name         = data.azurerm_resource_group.ws.name
  source_port_range           = "*"
}
