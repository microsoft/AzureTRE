# -------------------------------------------------------------------
# Fabric Capacity (Azure resource via azurerm provider)
# -------------------------------------------------------------------
resource "azurerm_fabric_capacity" "fabric" {
  name                = local.fabric_capacity_name
  resource_group_name = data.azurerm_resource_group.ws.name
  location            = data.azurerm_resource_group.ws.location

  administration_members = local.capacity_admin_ids

  sku {
    name = var.fabric_capacity_sku
    tier = "Fabric"
  }

  tags = local.workspace_service_tags

  lifecycle {
    ignore_changes = [tags]
  }
}

# -------------------------------------------------------------------
# Wait for the Fabric API to register the newly created capacity.
# ARM creation completes before the Fabric control plane is ready.
# -------------------------------------------------------------------
resource "time_sleep" "wait_for_capacity" {
  depends_on      = [azurerm_fabric_capacity.fabric]
  create_duration = "120s"
}

# -------------------------------------------------------------------
# Fabric Capacity data source (reads the Fabric GUID from display name)
# -------------------------------------------------------------------
data "fabric_capacity" "this" {
  display_name = azurerm_fabric_capacity.fabric.name

  depends_on = [time_sleep.wait_for_capacity]

  lifecycle {
    postcondition {
      condition     = self.state == "Active"
      error_message = "Fabric Capacity '${azurerm_fabric_capacity.fabric.name}' is not in Active state (current: ${self.state})."
    }
  }
}

# -------------------------------------------------------------------
# Fabric Workspace
# -------------------------------------------------------------------
resource "fabric_workspace" "researchers" {
  display_name = local.fabric_workspace_name
  description  = "TRE Workspace ${var.workspace_id} - Fabric analytics environment"
  capacity_id  = data.fabric_capacity.this.id

  timeouts = {
    create = "30m"
    update = "30m"
    delete = "30m"
  }
}

# -------------------------------------------------------------------
# Assign TRE workspace AAD groups to the Fabric workspace.
# Workspace Owners group → Admin role
# Workspace Researchers group → Contributor role
# -------------------------------------------------------------------
resource "fabric_workspace_role_assignment" "owners" {
  workspace_id = fabric_workspace.researchers.id

  principal = {
    id   = var.workspace_owners_group_id
    type = "Group"
  }

  role = "Admin"
}

resource "fabric_workspace_role_assignment" "researchers" {
  workspace_id = fabric_workspace.researchers.id

  principal = {
    id   = var.workspace_researchers_group_id
    type = "Group"
  }

  role = "Contributor"
}

# -------------------------------------------------------------------
# Default Lakehouse
# -------------------------------------------------------------------
resource "fabric_lakehouse" "default" {
  display_name = local.lakehouse_name
  description  = "Default Lakehouse for TRE workspace ${var.workspace_id}"
  workspace_id = fabric_workspace.researchers.id

  configuration = {
    enable_schemas = true
  }

  timeouts = {
    create = "10m"
    update = "10m"
    delete = "10m"
  }
}

# -------------------------------------------------------------------
# Wait for the Fabric managed VNet to be ready before creating PEs.
# The workspace must be fully initialised or PE creation may fail
# with transient "UnknownError" responses from the Fabric API.
# -------------------------------------------------------------------
resource "time_sleep" "wait_for_managed_vnet" {
  depends_on      = [fabric_workspace.researchers]
  create_duration = "30s"
}

# -------------------------------------------------------------------
# Managed Private Endpoints (outbound from Fabric to workspace storage)
# These allow Fabric Spark workloads to securely access the workspace
# storage account without traversing the public internet.
#
# The endpoints are serialised (dfs depends_on blob) to avoid
# concurrent-write errors against the Fabric control-plane.
# -------------------------------------------------------------------
resource "fabric_workspace_managed_private_endpoint" "blob" {
  workspace_id                    = fabric_workspace.researchers.id
  name                            = "pe-blob-${local.short_service_id}"
  target_private_link_resource_id = data.azurerm_storage_account.stg.id
  target_subresource_type         = "blob"
  request_message                 = local.managed_pe_request_messages.blob

  depends_on = [time_sleep.wait_for_managed_vnet]

  timeouts = {
    create = "10m"
    delete = "10m"
  }
}

resource "fabric_workspace_managed_private_endpoint" "dfs" {
  workspace_id                    = fabric_workspace.researchers.id
  name                            = "pe-dfs-${local.short_service_id}"
  target_private_link_resource_id = data.azurerm_storage_account.stg.id
  target_subresource_type         = "dfs"
  request_message                 = local.managed_pe_request_messages.dfs

  depends_on = [fabric_workspace_managed_private_endpoint.blob]

  timeouts = {
    create = "10m"
    delete = "10m"
  }
}

# -------------------------------------------------------------------
# Approve the managed PE connections on the workspace storage account.
#
# Fabric creates managed PEs from its managed VNet, but these appear
# as "Pending" on the target storage account and require explicit
# approval. Only connections whose request message exactly matches
# the ones set above are approved, and each must resolve to exactly
# one connection, so unrelated pending requests are never approved.
# -------------------------------------------------------------------
data "azapi_resource_list" "storage_pe_connections" {
  type      = "Microsoft.Storage/storageAccounts/privateEndpointConnections@2023-05-01"
  parent_id = data.azurerm_storage_account.stg.id

  response_export_values = {
    connections = "value[].{id: id, status: properties.privateLinkServiceConnectionState.status, description: properties.privateLinkServiceConnectionState.description}"
  }

  depends_on = [
    fabric_workspace_managed_private_endpoint.blob,
    fabric_workspace_managed_private_endpoint.dfs,
  ]

  lifecycle {
    postcondition {
      condition = alltrue([
        for msg in values(local.managed_pe_request_messages) : length(try([
          for c in self.output.connections : c.id
          if c.description == msg && contains(["Pending", "Approved"], c.status)
        ], [])) == 1
      ])
      error_message = "Expected exactly one Pending or Approved private endpoint connection per Fabric managed private endpoint request message on storage account ${data.azurerm_storage_account.stg.name}."
    }
  }
}

resource "azapi_resource_action" "approve_managed_pe_connection" {
  for_each = local.managed_pe_request_messages

  type        = "Microsoft.Storage/storageAccounts/privateEndpointConnections@2023-05-01"
  resource_id = local.managed_pe_connection_ids[each.key]
  method      = "PUT"

  # Keep the request message as the description so the connection can
  # still be matched on subsequent plans.
  body = {
    properties = {
      privateLinkServiceConnectionState = {
        status      = "Approved"
        description = each.value
      }
    }
  }

  response_export_values = {
    status = "properties.privateLinkServiceConnectionState.status"
  }

  lifecycle {
    postcondition {
      condition     = self.output.status == "Approved"
      error_message = "Failed to approve the Fabric managed private endpoint connection ${each.key} on storage account ${data.azurerm_storage_account.stg.name}."
    }
  }
}

# -------------------------------------------------------------------
# Custom Spark Pool
#
# Starter Pools do NOT support Managed Private Endpoints or Private
# Links.  A Custom Pool is required so that Spark sessions route
# traffic through the workspace managed VNet and its approved PEs.
#
# Node sizing is kept minimal (Small / single-node) to work within
# F2 capacity (4 Spark VCores).  Larger SKUs can increase max nodes.
# -------------------------------------------------------------------
resource "fabric_spark_custom_pool" "default" {
  workspace_id = fabric_workspace.researchers.id
  name         = "tre-pool-${local.short_service_id}"
  node_family  = "MemoryOptimized"
  node_size    = "Small"
  type         = "Workspace"

  auto_scale = {
    enabled        = true
    min_node_count = 1
    max_node_count = 1
  }

  dynamic_executor_allocation = {
    enabled       = true
    min_executors = 1
    max_executors = 1
  }

  depends_on = [azapi_resource_action.approve_managed_pe_connection]

  timeouts = {
    create = "10m"
    update = "10m"
    delete = "10m"
  }
}

# -------------------------------------------------------------------
# Spark Workspace Settings
#
# Point the workspace at the custom pool so all notebook / Spark-job
# sessions use the managed VNet and can reach workspace storage via
# the approved managed private endpoints.
# -------------------------------------------------------------------
resource "fabric_spark_workspace_settings" "default" {
  workspace_id = fabric_workspace.researchers.id

  pool = {
    default_pool = {
      name = fabric_spark_custom_pool.default.name
      type = "Workspace"
    }
    starter_pool = {
      max_executors  = 1
      max_node_count = 1
    }
    customize_compute_enabled = true
  }

  automatic_log = {
    enabled = true
  }

  environment = {
    runtime_version = "1.3"
  }

  depends_on = [fabric_spark_custom_pool.default]
}

# -------------------------------------------------------------------
# Provision the Fabric managed VNet.
#
# The managed VNet is only provisioned when the first Spark session
# starts. There is no Fabric Terraform resource to run a notebook on
# demand, so this runs a temporary notebook via the Fabric REST API.
# It must complete before outbound public access is denied below.
# -------------------------------------------------------------------
resource "terraform_data" "provision_managed_vnet" {
  input = fabric_workspace.researchers.id

  provisioner "local-exec" {
    command = "/bin/sh ${path.module}/../provision_managed_vnet.sh ${fabric_workspace.researchers.id}"
  }

  depends_on = [fabric_spark_workspace_settings.default]
}

# -------------------------------------------------------------------
# Workspace network communication policy
#
# Outbound public access is denied so Fabric workloads can only reach
# resources via approved managed private endpoints. Inbound public
# access is kept as Allow so the resource processor can continue to
# manage the workspace through the Fabric API (it does not route via
# the workspace private link endpoint).
# -------------------------------------------------------------------
resource "fabric_workspace_network_communication_policy" "default" {
  workspace_id = fabric_workspace.researchers.id

  inbound = {
    public_access_rules = {
      default_action = "Allow"
    }
  }

  outbound = {
    public_access_rules = {
      default_action = "Deny"
    }
  }

  depends_on = [terraform_data.provision_managed_vnet]
}
