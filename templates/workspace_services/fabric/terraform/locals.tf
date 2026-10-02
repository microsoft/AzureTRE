locals {
  short_service_id               = substr(var.tre_resource_id, -4, -1)
  short_workspace_id             = substr(var.workspace_id, -4, -1)
  workspace_resource_name_suffix = "${var.tre_id}-ws-${local.short_workspace_id}"
  service_resource_name_suffix   = "${var.tre_id}-ws-${local.short_workspace_id}-svc-${local.short_service_id}"
  core_resource_group_name       = "rg-${var.tre_id}"

  # Fabric capacity name must be alphanumeric, 3-63 chars, start with a letter
  fabric_capacity_name = lower(replace("fc${local.service_resource_name_suffix}", "-", ""))

  fabric_workspace_name = "ws-${local.service_resource_name_suffix}"
  lakehouse_name        = "lh${local.short_service_id}"

  # Workspace shared storage account - same naming convention as base workspace
  storage_name = lower(replace("stg${substr(local.workspace_resource_name_suffix, -8, -1)}", "-", ""))

  workspace_service_tags = {
    tre_id                   = var.tre_id
    tre_workspace_id         = var.workspace_id
    tre_workspace_service_id = var.tre_resource_id
  }

  # Fabric capacity administration_members - only user/SP principals allowed (not groups)
  capacity_admin_ids = [
    data.azurerm_client_config.current.object_id,
  ]

  # Request messages identifying this service's managed PE connections on the workspace storage account
  managed_pe_request_messages = {
    blob = "TRE Fabric workspace service ${var.tre_resource_id} - blob access for workspace ${var.workspace_id}"
    dfs  = "TRE Fabric workspace service ${var.tre_resource_id} - dfs access for workspace ${var.workspace_id}"
  }

  managed_pe_connection_ids = {
    for k, msg in local.managed_pe_request_messages : k => one(try([
      for c in data.azapi_resource_list.storage_pe_connections.output.connections : c.id
      if c.description == msg && contains(["Pending", "Approved"], c.status)
    ], []))
  }

  # Extract the workspace-scoped API FQDN from the private endpoint DNS config
  # e.g. "9522917d...z95.w.api.privatelink.fabric.microsoft.com" → "9522917d...z95.w.api.fabric.microsoft.com"
  fabric_pe_record_sets = flatten([
    for cfg in azurerm_private_endpoint.fabric_workspace.private_dns_zone_configs : cfg.record_sets
  ])
  fabric_workspace_api_fqdn = replace(
    [for rs in local.fabric_pe_record_sets : rs.fqdn if length(regexall("\\.w\\.api\\.", rs.fqdn)) > 0][0],
    ".privatelink.", "."
  )
}
