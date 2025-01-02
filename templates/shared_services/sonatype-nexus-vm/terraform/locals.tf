locals {
  core_vnet                       = "vnet-${var.tre_id}"
  core_resource_group_name        = "rg-${var.tre_id}"
  nexus_allowed_fqdns             = "pypi.org,*.pypi.org,files.pythonhosted.org,security.ubuntu.com,archive.ubuntu.com,keyserver.ubuntu.com,repo.anaconda.com,*.docker.com,*.docker.io,conda.anaconda.org,azure.archive.ubuntu.com,packages.microsoft.com,repo.almalinux.org,download-ib01.fedoraproject.org,cran.r-project.org,cloud.r-project.org,download1.rstudio.org,*.snapcraftcontent.com,download.microsoft.com,marketplace.visualstudio.com"
  nexus_allowed_fqdns_list        = distinct(compact(split(",", replace(local.nexus_allowed_fqdns, " ", ""))))
  workspace_vm_allowed_fqdns      = "r3.o.lencr.org,x1.c.lencr.org"
  workspace_vm_allowed_fqdns_list = distinct(compact(split(",", replace(local.workspace_vm_allowed_fqdns, " ", ""))))
  storage_account_name            = lower(replace("stg-${var.tre_id}", "-", ""))
  tre_shared_service_tags = {
    tre_id                = var.tre_id
    tre_shared_service_id = var.tre_resource_id
  }
  cmk_name                 = "tre-encryption-${var.tre_id}"
  encryption_identity_name = "id-encryption-${var.tre_id}"
}
