resource "azurerm_virtual_network" "ws" {
  name                = "vnet-${local.workspace_resource_name_suffix}"
  location            = var.location
  resource_group_name = var.ws_resource_group_name
  address_space       = local.address_spaces
  tags                = var.tre_workspace_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_subnet" "services" {
  name                 = "ServicesSubnet"
  virtual_network_name = azurerm_virtual_network.ws.name
  resource_group_name  = var.ws_resource_group_name
  address_prefixes     = [local.services_subnet_address_prefix]
  # notice that private endpoints do not adhere to NSG rules
  private_endpoint_network_policies_enabled     = false
  private_link_service_network_policies_enabled = true
}

resource "azurerm_subnet" "webapps" {
  name                 = "WebAppsSubnet"
  virtual_network_name = azurerm_virtual_network.ws.name
  resource_group_name  = var.ws_resource_group_name
  address_prefixes     = [local.webapps_subnet_address_prefix]
  # notice that private endpoints do not adhere to NSG rules
  private_endpoint_network_policies_enabled     = false
  private_link_service_network_policies_enabled = true

  delegation {
    name = "delegation"

    service_delegation {
      name    = "Microsoft.Web/serverFarms"
      actions = ["Microsoft.Network/virtualNetworks/subnets/action"]
    }
  }

  depends_on = [
    # meant to resolve AnotherOperation errors with one operation in the vnet at a time
    azurerm_subnet.services
  ]
}

resource "azurerm_virtual_network_peering" "ws_core_peer" {
  name                      = "ws-core-peer-${local.workspace_resource_name_suffix}"
  resource_group_name       = var.ws_resource_group_name
  virtual_network_name      = azurerm_virtual_network.ws.name
  remote_virtual_network_id = data.azurerm_virtual_network.core.id
}

moved {
  from = azurerm_virtual_network_peering.ws-core-peer
  to   = azurerm_virtual_network_peering.ws_core_peer
}

resource "azurerm_virtual_network_peering" "core_ws_peer" {
  name                      = "core-ws-peer-${local.workspace_resource_name_suffix}"
  resource_group_name       = local.core_resource_group_name
  virtual_network_name      = local.core_vnet
  remote_virtual_network_id = azurerm_virtual_network.ws.id
}

moved {
  from = azurerm_virtual_network_peering.core-ws-peer
  to   = azurerm_virtual_network_peering.core_ws_peer
}

resource "azurerm_subnet_route_table_association" "rt_services_subnet_association" {
  route_table_id = data.azurerm_route_table.rt.id
  subnet_id      = azurerm_subnet.services.id
  depends_on = [
    # meant to resolve AnotherOperation errors with one operation in the vnet at a time
    azurerm_subnet.webapps
  ]
}

data "azurerm_client_config" "current" {}

resource "null_resource" "az_login_sp" {

  count = var.arm_use_msi == true ? 0 : 1
  provisioner "local-exec" {
    command = "az cloud set --name ${var.azure_environment} && az login --service-principal --username ${var.arm_client_id} --password ${var.arm_client_secret} --tenant ${var.arm_tenant_id}"
  }

  triggers = {
    timestamp = timestamp()
  }

}

resource "null_resource" "az_login_msi" {

  count = var.arm_use_msi == true ? 1 : 0
  provisioner "local-exec" {
    command = "az cloud set --name ${var.azure_environment} && az login --identity -u '${data.azurerm_client_config.current.client_id}'"
  }

  triggers = {
    timestamp = timestamp()
  }
}

resource "null_resource" "ws_core_peer_sync" {
  depends_on = [
    azurerm_virtual_network_peering.core_ws_peer,
    null_resource.az_login_sp,
    null_resource.az_login_msi
  ]
  triggers = {
    vnet2addr = join(",", azurerm_virtual_network.ws.address_space)
  }
  provisioner "local-exec" {
    command = <<CMD
         az network vnet peering sync --ids ${azurerm_virtual_network_peering.ws_core_peer.id}
    CMD
  }
}

resource "null_resource" "core_ws_sync" {
  depends_on = [
    azurerm_virtual_network_peering.core_ws_peer,
    null_resource.az_login_sp,
    null_resource.az_login_msi
  ]
  triggers = {
    vnet2addr = join(",", azurerm_virtual_network.ws.address_space)
  }
  provisioner "local-exec" {
    command = <<CMD
        az network vnet peering sync --ids ${azurerm_virtual_network_peering.core_ws_peer.id}
    CMD
  }
}

resource "azurerm_subnet_route_table_association" "rt_webapps_subnet_association" {
  route_table_id = data.azurerm_route_table.rt.id
  subnet_id      = azurerm_subnet.webapps.id
  depends_on = [
    # meant to resolve AnotherOperation errors with one operation in the vnet at a time
    azurerm_subnet_route_table_association.rt_services_subnet_association
  ]
}

module "terraform_azurerm_environment_configuration" {
  source          = "git::https://github.com/microsoft/terraform-azurerm-environment-configuration.git?ref=fa7a3809a24f97d43737eaf72ed13eaef70fb369"
  arm_environment = var.arm_environment
}
