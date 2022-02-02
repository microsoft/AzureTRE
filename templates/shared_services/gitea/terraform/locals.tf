locals {
  core_vnet                = "vnet-${var.tre_id}"
  core_resource_group_name = "rg-${var.tre_id}"
  webapp_name              = "gitea-${var.tre_id}"
  firewall_name            = "fw-${var.tre_id}"
  storage_account_name     = "stg${var.tre_id}"
  keyvault_name            = "kv-${var.tre_id}"
  version                  = replace(replace(replace(data.local_file.version.content, "__version__ = \"", ""), "\"", ""), "\n", "")
  gitea_allowed_fqdns_list = distinct(compact(split(",", replace(var.gitea_allowed_fqdns, " ", ""))))
}
