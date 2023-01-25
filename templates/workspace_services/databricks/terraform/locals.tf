locals {
  databricks_subnets             = cidrsubnets(var.address_space, 1, 1)
  container_subnet_address_space = local.databricks_subnets[0] # .0 - .127
  host_subnet_address_space      = local.databricks_subnets[1] # .128 - .254
  short_service_id               = substr(var.tre_resource_id, -4, -1)
  short_workspace_id             = substr(var.workspace_id, -4, -1)
  workspace_resource_name_suffix = "${var.tre_id}-ws-${local.short_workspace_id}"
  service_resource_name_suffix   = "${var.tre_id}-ws-${local.short_workspace_id}-svc-${local.short_service_id}"
  resource_group_name            = "rg-${var.tre_id}-ws-${local.short_workspace_id}"
  virtual_network_name           = "vnet-${local.workspace_resource_name_suffix}"
  core_resource_group_name       = "rg-${var.tre_id}"
  firewall_name                  = "fw-${var.tre_id}"
  databricks_workspace_name      = "adb-${local.service_resource_name_suffix}"
  managed_resource_group_name    = "rg-${local.service_resource_name_suffix}"
  host_subnet_name               = "adb-host-subnet-${local.service_resource_name_suffix}"
  container_subnet_name          = "adb-container-subnet-${local.service_resource_name_suffix}"
  network_security_group_name    = "nsg-${local.service_resource_name_suffix}"
  route_table_name               = "rt-${local.service_resource_name_suffix}"
  # databricks-udr.json was build according to this page https://learn.microsoft.com/en-us/azure/databricks/administration-guide/cloud-configurations/azure/udr
  map_location_url_config = jsondecode(file("${path.module}/databricks-udr.json"))
  storage_name            = lower(replace("stgdbfs${substr(local.service_resource_name_suffix, -8, -1)}", "-", ""))

  tre_workspace_service_tags = {
    tre_id                   = var.tre_id
    tre_workspace_id         = var.workspace_id
    tre_workspace_service_id = var.tre_resource_id
  }
}
