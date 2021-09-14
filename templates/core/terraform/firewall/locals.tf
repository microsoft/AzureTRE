locals {
  nexus_allowed_fqdns_list = distinct(compact(split(",", replace(var.nexus_allowed_fqdns, " ", ""))))
  gitea_allowed_fqdns_list = distinct(compact(split(",", replace(var.gitea_allowed_fqdns, " ", ""))))
}
