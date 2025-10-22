locals {
  core_vnet                       = "vnet-${var.tre_id}"
  core_resource_group_name        = "rg-${var.tre_id}"
  nexus_allowed_fqdns             = "pypi.org,*.pypi.org,files.pythonhosted.org,security.ubuntu.com,archive.ubuntu.com,keyserver.ubuntu.com,repo.anaconda.com,*.docker.com,*.docker.io,conda.anaconda.org,azure.archive.ubuntu.com,packages.microsoft.com,repo.almalinux.org,download-ib01.fedoraproject.org,cran.r-project.org,cloud.r-project.org"
  nexus_allowed_fqdns_list        = distinct(compact(split(",", replace(local.nexus_allowed_fqdns, " ", ""))))
  # workspace_vm_allowed_fqdns      = "r3.o.lencr.org,x1.c.lencr.org,e5.o.lencr.org,e5.i.lencr.org,e6.o.lencr.org,e6.i.lencr.org,e5.c.lencr.org,e6.c.lencr.org,e7.c.lencr.org"
  workspace_vm_allowed_fqdns      = "*.o.lencr.org,*.c.lencr.org,*.i.lencr.org"
  workspace_vm_allowed_fqdns_list = distinct(compact(split(",", replace(local.workspace_vm_allowed_fqdns, " ", ""))))
  storage_account_name            = lower(replace("stg-${var.tre_id}", "-", ""))
  tre_shared_service_tags = {
    tre_id                = var.tre_id
    tre_shared_service_id = var.tre_resource_id
  }
}
