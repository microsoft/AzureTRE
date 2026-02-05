# Consolidated Workspace Airlock Storage Account
# This replaces 5 separate storage accounts with 1 consolidated account using metadata-based stage management
#
# Previous architecture (5 storage accounts per workspace):
# - stalimappws{ws_id} (import-approved)
# - stalexintws{ws_id} (export-internal)
# - stalexipws{ws_id} (export-inprogress)
# - stalexrejws{ws_id} (export-rejected)
# - stalexblockedws{ws_id} (export-blocked)
#
# New architecture (1 storage account per workspace):
# - stalairlockws{ws_id} with containers named: {request_id}
# - Container metadata tracks stage: stage=import-approved, stage=export-internal, etc.

resource "azurerm_storage_account" "sa_airlock_workspace" {
  name                             = local.airlock_workspace_storage_name
  location                         = var.location
  resource_group_name              = var.ws_resource_group_name
  account_tier                     = "Standard"
  account_replication_type         = "LRS"
  table_encryption_key_type        = var.enable_cmk_encryption ? "Account" : "Service"
  queue_encryption_key_type        = var.enable_cmk_encryption ? "Account" : "Service"
  allow_nested_items_to_be_public  = false
  cross_tenant_replication_enabled = false
  shared_access_key_enabled        = false
  local_user_enabled               = false

  # Important! we rely on the fact that the blob created events are issued when the creation of the blobs are done.
  # This is true ONLY when Hierarchical Namespace is DISABLED
  is_hns_enabled = false

  # changing this value is destructive, hence attribute is in lifecycle.ignore_changes block below
  infrastructure_encryption_enabled = true

  network_rules {
    default_action = var.enable_local_debugging ? "Allow" : "Deny"
    bypass         = ["AzureServices"]
    
    # The Airlock processor needs to access workspace storage accounts
    virtual_network_subnet_ids = [var.airlock_processor_subnet_id]
  }

  dynamic "identity" {
    for_each = var.enable_cmk_encryption ? [1] : []
    content {
      type         = "UserAssigned"
      identity_ids = [var.encryption_identity_id]
    }
  }

  dynamic "customer_managed_key" {
    for_each = var.enable_cmk_encryption ? [1] : []
    content {
      key_vault_key_id          = var.encryption_key_versionless_id
      user_assigned_identity_id = var.encryption_identity_id
    }
  }

  tags = merge(
    var.tre_workspace_tags,
    {
      description = "airlock;workspace;consolidated"
    }
  )

  lifecycle { ignore_changes = [infrastructure_encryption_enabled, tags] }
}

# Enable Airlock Malware Scanning on Workspace
resource "azapi_resource_action" "enable_defender_for_storage_workspace" {
  count       = var.enable_airlock_malware_scanning ? 1 : 0
  type        = "Microsoft.Security/defenderForStorageSettings@2022-12-01-preview"
  resource_id = "${azurerm_storage_account.sa_airlock_workspace.id}/providers/Microsoft.Security/defenderForStorageSettings/current"
  method      = "PUT"

  body = {
    properties = {
      isEnabled = true
      malwareScanning = {
        onUpload = {
          isEnabled     = true
          capGBPerMonth = 5000
        },
        scanResultsEventGridTopicResourceId = data.azurerm_eventgrid_topic.scan_result[0].id
      }
      sensitiveDataDiscovery = {
        isEnabled = false
      }
      overrideSubscriptionLevelSettings = true
    }
  }
}

# Single Private Endpoint for Consolidated Workspace Storage Account
# This replaces 5 separate private endpoints
resource "azurerm_private_endpoint" "airlock_workspace_pe" {
  name                = "pe-sa-airlock-ws-blob-${var.short_workspace_id}"
  location            = var.location
  resource_group_name = var.ws_resource_group_name
  subnet_id           = var.services_subnet_id
  tags                = var.tre_workspace_tags

  lifecycle { ignore_changes = [tags] }

  private_dns_zone_group {
    name                 = "private-dns-zone-group-sa-airlock-ws"
    private_dns_zone_ids = [data.azurerm_private_dns_zone.blobcore.id]
  }

  private_service_connection {
    name                           = "psc-sa-airlock-ws-${var.short_workspace_id}"
    private_connection_resource_id = azurerm_storage_account.sa_airlock_workspace.id
    is_manual_connection           = false
    subresource_names              = ["Blob"]
  }
}

# System EventGrid Topics for Blob Created Events
# These topics subscribe to blob creation events in the consolidated workspace storage account

# Import Approved Blob Created Events
resource "azurerm_eventgrid_system_topic" "import_approved_blob_created" {
  name                   = local.import_approved_sys_topic_name
  location               = var.location
  resource_group_name    = var.ws_resource_group_name
  source_arm_resource_id = azurerm_storage_account.sa_airlock_workspace.id
  topic_type             = "Microsoft.Storage.StorageAccounts"
  tags                   = var.tre_workspace_tags

  identity {
    type = "SystemAssigned"
  }

  lifecycle { ignore_changes = [tags] }
}

# Export In-Progress Blob Created Events
resource "azurerm_eventgrid_system_topic" "export_inprogress_blob_created" {
  name                   = local.export_inprogress_sys_topic_name
  location               = var.location
  resource_group_name    = var.ws_resource_group_name
  source_arm_resource_id = azurerm_storage_account.sa_airlock_workspace.id
  topic_type             = "Microsoft.Storage.StorageAccounts"
  tags                   = var.tre_workspace_tags

  identity {
    type = "SystemAssigned"
  }

  lifecycle { ignore_changes = [tags] }
}

# Export Rejected Blob Created Events
resource "azurerm_eventgrid_system_topic" "export_rejected_blob_created" {
  name                   = local.export_rejected_sys_topic_name
  location               = var.location
  resource_group_name    = var.ws_resource_group_name
  source_arm_resource_id = azurerm_storage_account.sa_airlock_workspace.id
  topic_type             = "Microsoft.Storage.StorageAccounts"
  tags                   = var.tre_workspace_tags

  identity {
    type = "SystemAssigned"
  }

  lifecycle { ignore_changes = [tags] }
}

# Export Blocked Blob Created Events
resource "azurerm_eventgrid_system_topic" "export_blocked_blob_created" {
  name                   = local.export_blocked_sys_topic_name
  location               = var.location
  resource_group_name    = var.ws_resource_group_name
  source_arm_resource_id = azurerm_storage_account.sa_airlock_workspace.id
  topic_type             = "Microsoft.Storage.StorageAccounts"
  tags                   = var.tre_workspace_tags

  identity {
    type = "SystemAssigned"
  }

  lifecycle { ignore_changes = [tags] }
}

# Role Assignments for EventGrid System Topics to send to Service Bus
resource "azurerm_role_assignment" "servicebus_sender_import_approved_blob_created" {
  scope                = data.azurerm_servicebus_namespace.airlock_sb.id
  role_definition_name = "Azure Service Bus Data Sender"
  principal_id         = azurerm_eventgrid_system_topic.import_approved_blob_created.identity[0].principal_id

  depends_on = [
    azurerm_eventgrid_system_topic.import_approved_blob_created
  ]
}

resource "azurerm_role_assignment" "servicebus_sender_export_inprogress_blob_created" {
  scope                = data.azurerm_servicebus_namespace.airlock_sb.id
  role_definition_name = "Azure Service Bus Data Sender"
  principal_id         = azurerm_eventgrid_system_topic.export_inprogress_blob_created.identity[0].principal_id

  depends_on = [
    azurerm_eventgrid_system_topic.export_inprogress_blob_created
  ]
}

resource "azurerm_role_assignment" "servicebus_sender_export_rejected_blob_created" {
  scope                = data.azurerm_servicebus_namespace.airlock_sb.id
  role_definition_name = "Azure Service Bus Data Sender"
  principal_id         = azurerm_eventgrid_system_topic.export_rejected_blob_created.identity[0].principal_id

  depends_on = [
    azurerm_eventgrid_system_topic.export_rejected_blob_created
  ]
}

resource "azurerm_role_assignment" "servicebus_sender_export_blocked_blob_created" {
  scope                = data.azurerm_servicebus_namespace.airlock_sb.id
  role_definition_name = "Azure Service Bus Data Sender"
  principal_id         = azurerm_eventgrid_system_topic.export_blocked_blob_created.identity[0].principal_id

  depends_on = [
    azurerm_eventgrid_system_topic.export_blocked_blob_created
  ]
}

# Role Assignments for Consolidated Workspace Storage Account

# Airlock Processor Identity - needs access to all workspace containers
resource "azurerm_role_assignment" "airlock_workspace_blob_data_contributor" {
  scope                = azurerm_storage_account.sa_airlock_workspace.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = data.azurerm_user_assigned_identity.airlock_id.principal_id
}

# API Identity - needs access to approved, internal, and in-progress containers
resource "azurerm_role_assignment" "api_workspace_blob_data_contributor" {
  scope                = azurerm_storage_account.sa_airlock_workspace.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = data.azurerm_user_assigned_identity.api_id.principal_id
}
