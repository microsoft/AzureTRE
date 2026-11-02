locals {
  core_resource_group_name = "rg-${var.tre_id}"
  core_vnet                = "vnet-${var.tre_id}"
  short_service_id         = substr(var.tre_resource_id, -4, -1)
  # A range with host bits, for example 10.1.4.5/24, becomes its network address, 10.1.4.0/24.
  cluster_address_spaces = distinct([
    for cidr in jsondecode(base64decode(var.cluster_address_spaces)) :
    "${cidrhost(cidr, 0)}/${split("/", cidr)[1]}"
  ])
  vm_name      = "cyclecloud-${local.short_service_id}"
  storage_name = lower(replace("stgcc${var.tre_id}${local.short_service_id}", "-", ""))
  tre_shared_service_tags = {
    tre_id                = var.tre_id
    tre_shared_service_id = var.tre_resource_id
  }
  cmk_name                 = "tre-encryption-${var.tre_id}"
  encryption_identity_name = "id-encryption-${var.tre_id}"
}
