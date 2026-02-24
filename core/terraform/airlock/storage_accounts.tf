

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
  public_network_access_enabled    = true

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

  # Core storage is publicly accessible for user-facing stages (import-draft, export-approved)
  # matching the original sa_import_external / sa_export_approved security model.
  # Security is enforced by:
  #   - ABAC conditions on role assignments (API restricted to import-external + export-approved stages)
  #   - User delegation SAS tokens (inherit ABAC restrictions of the signing identity)
  #   - SAS tokens are only generated for publicly-accessible stages
  # Internal stages (in-progress, rejected, blocked) are protected by ABAC even though
  # the storage account allows public network access.
  network_rules {
    default_action = "Allow"
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

# Private Endpoint #1: From Airlock Storage Subnet (Processor Access)
# For airlock processor to access all stages
resource "azurerm_private_endpoint" "stg_airlock_core_pe_processor" {
  name                = "pe-stg-airlock-processor-${var.tre_id}"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.airlock_storage_subnet_id
  tags                = var.tre_core_tags

  lifecycle { ignore_changes = [tags] }

  private_dns_zone_group {
    name                 = "pdzg-stg-airlock-processor-${var.tre_id}"
    private_dns_zone_ids = [var.blob_core_dns_zone_id]
  }

  private_service_connection {
    name                           = "psc-stg-airlock-processor-${var.tre_id}"
    private_connection_resource_id = azurerm_storage_account.sa_airlock_core.id
    is_manual_connection           = false
    subresource_names              = ["Blob"]
  }
}

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
  principal_id         = azurerm_user_assigned_identity.airlock_id.principal_id
}

# API Identity - restricted access using ABAC to specific stages and private endpoints
# API accesses via processor PE and can access import-external, export-approved
resource "azurerm_role_assignment" "api_core_blob_data_contributor" {
  scope                = azurerm_storage_account.sa_airlock_core.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = var.api_principal_id

  # ABAC condition: Restrict blob operations to specific stages only
  # Logic: Allow if (action is NOT a blob operation) OR (action is blob operation AND stage matches)
  # This allows container operations (list, etc.) while restricting blob read/write/delete to allowed stages
  condition_version = "2.0"
  condition         = <<-EOT
    (
      (
        !(ActionMatches{'Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read'})
        AND !(ActionMatches{'Microsoft.Storage/storageAccounts/blobServices/containers/blobs/write'})
        AND !(ActionMatches{'Microsoft.Storage/storageAccounts/blobServices/containers/blobs/add/action'})
        AND !(ActionMatches{'Microsoft.Storage/storageAccounts/blobServices/containers/blobs/delete'})
      )
      OR
      @Resource[Microsoft.Storage/storageAccounts/blobServices/containers/metadata:stage]
        StringEquals 'import-external'
      OR
      @Resource[Microsoft.Storage/storageAccounts/blobServices/containers/metadata:stage]
        StringEquals 'export-approved'
    )
  EOT
}

resource "azurerm_storage_account" "sa_airlock_workspace_global" {
  name                             = local.airlock_workspace_global_storage_name
  location                         = var.location
  resource_group_name              = var.resource_group_name
  account_tier                     = "Standard"
  account_replication_type         = "LRS"
  table_encryption_key_type        = var.enable_cmk_encryption ? "Account" : "Service"
  queue_encryption_key_type        = var.enable_cmk_encryption ? "Account" : "Service"
  allow_nested_items_to_be_public  = false
  cross_tenant_replication_enabled = false
  shared_access_key_enabled        = false
  local_user_enabled               = false

  # Important! we rely on the fact that the blob craeted events are issued when the creation of the blobs are done.
  # This is true ONLY when Hierarchical Namespace is DISABLED
  is_hns_enabled = false

  # changing this value is destructive, hence attribute is in lifecycle.ignore_changes block below
  infrastructure_encryption_enabled = true

  network_rules {
    default_action = var.enable_local_debugging ? "Allow" : "Deny"
    bypass         = ["AzureServices"]
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

  tags = merge(var.tre_core_tags, {
    description = "airlock;workspace;global"
  })

  lifecycle { ignore_changes = [infrastructure_encryption_enabled, tags] }
}


resource "azapi_resource_action" "enable_defender_for_storage_workspace_global" {
  count       = var.enable_malware_scanning ? 1 : 0
  type        = "Microsoft.Security/defenderForStorageSettings@2022-12-01-preview"
  resource_id = "${azurerm_storage_account.sa_airlock_workspace_global.id}/providers/Microsoft.Security/defenderForStorageSettings/current"
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


resource "azurerm_eventgrid_system_topic" "airlock_workspace_global_blob_created" {
  name                   = "evgt-airlock-blob-created-global-${var.tre_id}"
  location               = var.location
  resource_group_name    = var.resource_group_name
  source_arm_resource_id = azurerm_storage_account.sa_airlock_workspace_global.id
  topic_type             = "Microsoft.Storage.StorageAccounts"
  tags                   = var.tre_core_tags

  identity {
    type = "SystemAssigned"
  }

  lifecycle { ignore_changes = [tags] }
}

# Role Assignment for Global Workspace EventGrid System Topic
resource "azurerm_role_assignment" "servicebus_sender_airlock_workspace_global_blob_created" {
  scope                = var.airlock_servicebus.id
  role_definition_name = "Azure Service Bus Data Sender"
  principal_id         = azurerm_eventgrid_system_topic.airlock_workspace_global_blob_created.identity[0].principal_id

  depends_on = [
    azurerm_eventgrid_system_topic.airlock_workspace_global_blob_created
  ]
}

# Private Endpoint for workspace global storage (processor access via private endpoint, not service endpoint)
resource "azurerm_private_endpoint" "stg_airlock_workspace_global_pe_processor" {
  name                = "pe-stg-airlock-ws-global-${var.tre_id}"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.airlock_storage_subnet_id
  tags                = var.tre_core_tags

  lifecycle { ignore_changes = [tags] }

  private_dns_zone_group {
    name                 = "pdzg-stg-airlock-ws-global-${var.tre_id}"
    private_dns_zone_ids = [var.blob_core_dns_zone_id]
  }

  private_service_connection {
    name                           = "psc-stg-airlock-ws-global-${var.tre_id}"
    private_connection_resource_id = azurerm_storage_account.sa_airlock_workspace_global.id
    is_manual_connection           = false
    subresource_names              = ["Blob"]
  }
}

# Airlock Processor Identity - needs access to all workspace containers (no restrictions)
resource "azurerm_role_assignment" "airlock_workspace_global_blob_data_contributor" {
  scope                = azurerm_storage_account.sa_airlock_workspace_global.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.airlock_id.principal_id
}
