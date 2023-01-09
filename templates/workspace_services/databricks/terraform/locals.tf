locals {
  databricks_subnets = cidrsubnets(var.address_space, 1, 1)

  private_subnet_address_space = local.databricks_subnets[0] # .0 - .127
  public_subnet_address_space  = local.databricks_subnets[1] # .128 - .254

  short_workspace_id             = substr(var.workspace_id, -4, -1)
  workspace_resource_name_suffix = "${var.tre_id}-ws-${local.short_workspace_id}"
  resource_group_name            = "rg-${local.workspace_resource_name_suffix}"
  keyvault_name                  = "kv-${local.workspace_resource_name_suffix}"
  storage_name                   = "stg${replace(local.workspace_resource_name_suffix, "-", "")}"
  virtual_network_name           = "vnet-${local.workspace_resource_name_suffix}"
  core_resource_group_name       = "rg-${var.tre_id}"
  firewall_name                  = "fw-${var.tre_id}"
  databricks_workspace_name      = "dbw-${local.workspace_resource_name_suffix}"
  managed_resource_group_name    = "mrg-db-${local.workspace_resource_name_suffix}"
  public_subnet_name             = "public-${local.workspace_resource_name_suffix}"
  private_subnet_name            = "private-${local.workspace_resource_name_suffix}"
  network_security_group_name    = "nsg-${local.workspace_resource_name_suffix}"
  route_table_name               = "rt-${local.workspace_resource_name_suffix}"

  mapLocationUrlConfig = jsondecode(file("${path.module}/databricks-udr.json"))

  tre_workspace_service_tags = {
    tre_id                   = var.tre_id
    tre_workspace_id         = var.workspace_id
    tre_workspace_service_id = var.tre_resource_id
  }
}
