# Consolidated Core Airlock Storage Account
# This replaces 5 separate storage accounts with 1 consolidated account using stage-prefixed containers
#
# Previous architecture (5 storage accounts):
# - stalimex{tre_id} (import-external)
# - stalimip{tre_id} (import-inprogress)
# - stalimrej{tre_id} (import-rejected)
# - stalimblocked{tre_id} (import-blocked)
# - stalexapp{tre_id} (export-approved)
#
# New architecture (1 storage account):
# - stalairlock{tre_id} with containers named: {stage}-{request_id}
#   - import-external-{request_id}
#   - import-inprogress-{request_id}
#   - import-rejected-{request_id}
#   - import-blocked-{request_id}
#   - export-approved-{request_id}

resource "azurerm_storage_account" "sa_airlock_core" {
  name                             = local.airlock_core_storage_name
  location                         = var.location
  resource_group_name              = var.resource_group_name
  account_tier                     = "Standard"
  account_replication_type         = "LRS"
  table_encryption_key_type        = var.enable_cmk_encryption ? "Account" : "Service"
  queue_encryption_key_type        = var.enable_cmk_encryption ? "Account" : "Service"
  cross_tenant_replication_enabled = false
  shared_access_key_enabled        = false
  local_user_enabled               = false
  allow_nested_items_to_be_public  = false

  # Important! we rely on the fact that the blob created events are issued when the creation of the blobs are done.
  # This is true ONLY when Hierarchical Namespace is DISABLED
  is_hns_enabled = false

  # changing this value is destructive, hence attribute is in lifecycle.ignore_changes block below
  infrastructure_encryption_enabled = true

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

  network_rules {
    default_action = var.enable_local_debugging ? "Allow" : "Deny"
    bypass         = ["AzureServices"]
  }

  tags = merge(var.tre_core_tags, {
    description = "airlock;core;consolidated"
  })

  lifecycle { ignore_changes = [infrastructure_encryption_enabled, tags] }
}

# Enable Airlock Malware Scanning on Consolidated Core Storage Account
resource "azapi_resource_action" "enable_defender_for_storage_core" {
  count       = var.enable_malware_scanning ? 1 : 0
  type        = "Microsoft.Security/defenderForStorageSettings@2022-12-01-preview"
  resource_id = "${azurerm_storage_account.sa_airlock_core.id}/providers/Microsoft.Security/defenderForStorageSettings/current"
  method      = "PUT"

  body = {
    properties = {
      isEnabled = true
      malwareScanning = {
        onUpload = {
          isEnabled     = true
          capGBPerMonth = 5000
        },
        scanResultsEventGridTopicResourceId = azurerm_eventgrid_topic.scan_result[0].id
      }
      sensitiveDataDiscovery = {
        isEnabled = false
      }
      overrideSubscriptionLevelSettings = true
    }
  }
}

# Single Private Endpoint for Consolidated Core Storage Account
# This replaces 5 separate private endpoints
resource "azurerm_private_endpoint" "stg_airlock_core_pe" {
  name                = "pe-stg-airlock-core-blob-${var.tre_id}"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.airlock_storage_subnet_id
  tags                = var.tre_core_tags

  lifecycle { ignore_changes = [tags] }

  private_dns_zone_group {
    name                 = "pdzg-stg-airlock-core-blob-${var.tre_id}"
    private_dns_zone_ids = [var.blob_core_dns_zone_id]
  }

  private_service_connection {
    name                           = "psc-stg-airlock-core-blob-${var.tre_id}"
    private_connection_resource_id = azurerm_storage_account.sa_airlock_core.id
    is_manual_connection           = false
    subresource_names              = ["Blob"]
  }
}

# Unified System EventGrid Topic for All Blob Created Events
# This single topic replaces 4 separate stage-specific topics since we can't filter by container metadata
# The airlock processor will read container metadata to determine the actual stage
resource "azurerm_eventgrid_system_topic" "airlock_blob_created" {
  name                   = "evgt-airlock-blob-created-${var.tre_id}"
  location               = var.location
  resource_group_name    = var.resource_group_name
  source_arm_resource_id = azurerm_storage_account.sa_airlock_core.id
  topic_type             = "Microsoft.Storage.StorageAccounts"
  tags                   = var.tre_core_tags

  identity {
    type = "SystemAssigned"
  }

  lifecycle { ignore_changes = [tags] }
}

# Role Assignment for Unified EventGrid System Topic
resource "azurerm_role_assignment" "servicebus_sender_airlock_blob_created" {
  scope                = var.airlock_servicebus.id
  role_definition_name = "Azure Service Bus Data Sender"
  principal_id         = azurerm_eventgrid_system_topic.airlock_blob_created.identity[0].principal_id

  depends_on = [
    azurerm_eventgrid_system_topic.airlock_blob_created
  ]
}


# Role Assignments for Consolidated Core Storage Account

# Airlock Processor Identity - needs access to all containers (no restrictions)
resource "azurerm_role_assignment" "airlock_core_blob_data_contributor" {
  scope                = azurerm_storage_account.sa_airlock_core.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = data.azurerm_user_assigned_identity.airlock_id.principal_id
}

# API Identity - restricted access using ABAC to specific stages only
# API should only access: import-external (draft), import-inprogress (submitted/review), export-approved (final)
resource "azurerm_role_assignment" "api_core_blob_data_contributor" {
  scope                = azurerm_storage_account.sa_airlock_core.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = data.azurerm_user_assigned_identity.api_id.principal_id
  
  # ABAC condition to restrict API access to specific stages based on container metadata
  condition_version = "2.0"
  condition         = <<-EOT
    (
      !(ActionMatches{'Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read'} 
        OR ActionMatches{'Microsoft.Storage/storageAccounts/blobServices/containers/blobs/write'}
        OR ActionMatches{'Microsoft.Storage/storageAccounts/blobServices/containers/blobs/delete'})
      OR
      @Resource[Microsoft.Storage/storageAccounts/blobServices/containers].metadata['stage'] 
        StringIn ('import-external', 'import-in-progress', 'export-approved')
    )
  EOT
}
