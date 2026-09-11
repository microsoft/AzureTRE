locals {
  short_service_id               = substr(var.tre_resource_id, -4, -1)
  short_workspace_id             = substr(var.workspace_id, -4, -1)
  workspace_resource_name_suffix = "${var.tre_id}-ws-${local.short_workspace_id}"
  service_resource_name_suffix   = "${var.tre_id}-ws-${local.short_workspace_id}-svc-${local.short_service_id}"
  core_resource_group_name       = "rg-${var.tre_id}"
  keyvault_name                  = lower("kv-${substr(local.workspace_resource_name_suffix, -20, -1)}")
  storage_name                   = lower(replace("stg${substr(local.workspace_resource_name_suffix, -8, -1)}", "-", ""))
  session_host_name_prefix       = "avd${local.short_workspace_id}${local.short_service_id}"

  # AVD naming
  hostpool_name           = "hp-${local.service_resource_name_suffix}"
  avd_workspace_name      = "ws-${local.service_resource_name_suffix}"
  application_group_name  = "dag-${local.service_resource_name_suffix}"
  hostpool_friendly_name  = coalesce(trimspace(var.display_name), local.hostpool_name)
  workspace_friendly_name = coalesce(trimspace(var.workspace_display_name), "TRE Workspace ${local.short_workspace_id}")
  app_group_friendly_name = local.hostpool_friendly_name

  clipboard_transfer_direction          = var.enable_clipboard ? var.clipboard_transfer_direction : "disabled"
  clipboard_rdp_property                = local.clipboard_transfer_direction == "disabled" ? "redirectclipboard:i:0;" : "redirectclipboard:i:1;"
  authentication_rdp_properties         = "enablerdsaadauth:i:1;redirectwebauthn:i:1;"
  restricted_redirection_rdp_properties = "audiomode:i:2;audiocapturemode:i:0;drivestoredirect:s:;devicestoredirect:s:;usbdevicestoredirect:s:;redirectcomports:i:0;redirectprinters:i:0;redirectsmartcards:i:0;camerastoredirect:s:;"
  clipboard_server_to_client            = contains(["session_to_client", "both"], local.clipboard_transfer_direction) ? 4 : 0
  clipboard_client_to_server            = contains(["client_to_session", "both"], local.clipboard_transfer_direction) ? 4 : 0
  wvd_private_dns_zone_name             = var.arm_environment == "AzureUSGovernment" ? "privatelink.wvd.azure.us" : "privatelink.wvd.microsoft.com"
  avd_dsc_artifact_url                  = var.host_pool_type == "Pooled" ? "${data.azurerm_storage_account.stg.primary_blob_endpoint}${azurerm_storage_container.avd_artifacts[0].name}/Configuration.zip" : null
  avd_dsc_artifact_sha256               = split(" ", trimspace(file("${path.module}/../Configuration.zip.sha256")))[0]
  workspace_role_principal_ids          = toset([var.workspace_owners_group_id, var.workspace_researchers_group_id])

  workspace_service_tags = {
    tre_id                   = var.tre_id
    tre_workspace_id         = var.workspace_id
    tre_workspace_service_id = var.tre_resource_id
  }
}
