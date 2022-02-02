locals {
  core_vnet                = "vnet-${var.tre_id}"
  core_resource_group_name = "rg-${var.tre_id}"
  firewall_name            = "fw-${var.tre_id}"
  storage_account_name     = "stg${var.tre_id}"
  nexus_allowed_fqdns_list = distinct(compact(split(",", replace(var.nexus_allowed_fqdns, " ", ""))))
}
