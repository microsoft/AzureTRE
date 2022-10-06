locals {
  short_workspace_id             = substr(var.tre_resource_id, -4, -1)
  workspace_resource_name_suffix = "${var.tre_id}-ws-${local.short_workspace_id}"
  storage_name                   = lower(replace("stg${substr(local.workspace_resource_name_suffix, -8, -1)}", "-", ""))
  keyvault_name                  = lower("kv-${substr(local.workspace_resource_name_suffix, -20, -1)}")
  workspace_vm_allowed_fqdns     = "r3.o.lencr.org,x1.c.lencr.org,*.digicert.com,ocsp.godaddy.com,crl.godaddy.com"
  workspace_vm_allowed_fqdns_list = distinct(compact(split(",", replace(local.workspace_vm_allowed_fqdns, " ", ""))))
  tre_workspace_tags = {
    tre_id           = var.tre_id
    tre_workspace_id = var.tre_resource_id
  }
}
