locals {
  address_space                  = cidrsubnets("10.28.0.0/23", 1, 1)
  container_subnet_address_space = local.address_space[0] # private
  host_subnet_address_space      = local.address_space[1] # public
  short_service_id               = substr(var.tre_resource_id, -4, -1)
  service_resource_name_suffix   = "${var.tre_id}-svc-${local.short_service_id}"
  resource_group_name            = "rg-${var.tre_id}-svc-${local.short_service_id}"
  virtual_network_name           = "vnet-${local.service_resource_name_suffix}"
  core_virtual_network_name      = "vnet-${var.tre_id}"
  core_resource_group_name       = "rg-${var.tre_id}"
  databricks_workspace_name      = "adb-${local.service_resource_name_suffix}"
  managed_resource_group_name    = "rg-adb-${local.service_resource_name_suffix}"
  host_subnet_name               = "adb-host-subnet-${local.service_resource_name_suffix}"
  container_subnet_name          = "adb-container-subnet-${local.service_resource_name_suffix}"
  network_security_group_name    = "nsg-${local.service_resource_name_suffix}"

  tre_shared_service_tags = {
    tre_id                = var.tre_id
    tre_shared_service_id = var.tre_resource_id
  }
}
