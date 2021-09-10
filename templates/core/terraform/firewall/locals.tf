locals {
  nexus_allowed_fqdns_list = distinct(compact(split(",", var.nexus_allowed_fqdns)))
  gitea_allowed_fqdns_list = distinct(compact(split(",", var.gitea_allowed_fqdns)))
}
