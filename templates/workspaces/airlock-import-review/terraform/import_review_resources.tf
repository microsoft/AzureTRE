locals {
  core_resource_group_name = "rg-${var.tre_id}"
  # STorage AirLock IMport InProgress
  import_in_progress_storage_name = lower(replace("stalimip${var.tre_id}", "-", ""))
}

variable "ws_resource_group_name" {}
variable "services_subnet_id" {}
variable "tre_workspace_tags" {}

data "azurerm_storage_account" "sa_import_inprogress" {
  name                = local.import_in_progress_storage_name
  resource_group_name = local.core_resource_group_name
}

data "azurerm_private_dns_zone" "blobcore" {
  name                = "privatelink.blob.core.windows.net"
  resource_group_name = local.core_resource_group_name
}

resource "azurerm_private_endpoint" "sa_import_inprogress_pe" {
  name                = "stg-ip-import-blob-${local.workspace_resource_name_suffix}"
  location            = var.location
  resource_group_name = var.ws_resource_group_name
  subnet_id           = var.services_subnet_id

  lifecycle { ignore_changes = [tags] }

  private_dns_zone_group {
    name                 = "pdzg-stg-ip-import-blob-${local.workspace_resource_name_suffix}"
    private_dns_zone_ids = [data.azurerm_private_dns_zone.blobcore.id]
  }

  private_service_connection {
    name                           = "psc-stg-ip-import-blob-${local.workspace_resource_name_suffix}"
    private_connection_resource_id = data.azurerm_storage_account.sa_import_inprogress.id
    is_manual_connection           = false
    subresource_names              = ["Blob"]
  }

  tags = var.tre_workspace_tags
}
