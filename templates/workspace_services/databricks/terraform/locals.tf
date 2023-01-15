locals {
  databricks_subnets             = cidrsubnets(var.address_space, 1, 1)
  private_subnet_address_space   = local.databricks_subnets[0] # .0 - .127
  public_subnet_address_space    = local.databricks_subnets[1] # .128 - .254
  short_service_id               = substr(var.tre_resource_id, -4, -1)
  short_workspace_id             = substr(var.workspace_id, -4, -1)
  workspace_resource_name_suffix = "${var.tre_id}-ws-${local.short_workspace_id}"
  service_resource_name_suffix   = "${var.tre_id}-ws-${local.short_workspace_id}-svc-${local.short_service_id}"
  resource_group_name            = "rg-${var.tre_id}-ws-${local.short_workspace_id}"
  virtual_network_name           = "vnet-${local.workspace_resource_name_suffix}"
  core_resource_group_name       = "rg-${var.tre_id}"
  firewall_name                  = "fw-${var.tre_id}"
  databricks_workspace_name      = "dbw-${local.service_resource_name_suffix}"
  managed_resource_group_name    = "mrg-db-${local.service_resource_name_suffix}"
  public_subnet_name             = "public-${local.service_resource_name_suffix}"
  private_subnet_name            = "private-${local.service_resource_name_suffix}"
  network_security_group_name    = "nsg-${local.service_resource_name_suffix}"
  route_table_name               = "rt-${local.service_resource_name_suffix}"
  map_location_url_config        = jsondecode(file("${path.module}/databricks-udr.json"))

  tre_workspace_service_tags = {
    tre_id                   = var.tre_id
    tre_workspace_id         = var.workspace_id
    tre_workspace_service_id = var.tre_resource_id
  }
}

data "azurerm_subnet" "services" {
  name                 = "ServicesSubnet"
  virtual_network_name = data.azurerm_virtual_network.ws.name
  resource_group_name  = data.azurerm_virtual_network.ws.resource_group_name
}
