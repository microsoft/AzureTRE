resource "azurerm_storage_account" "stg" {
  name                             = local.storage_name
  resource_group_name              = azurerm_resource_group.ws.name
  location                         = azurerm_resource_group.ws.location
  account_tier                     = "Standard"
  account_replication_type         = var.storage_account_redundancy
  table_encryption_key_type        = var.enable_cmk_encryption ? "Account" : "Service"
  queue_encryption_key_type        = var.enable_cmk_encryption ? "Account" : "Service"
  allow_nested_items_to_be_public  = false
  is_hns_enabled                   = true
  cross_tenant_replication_enabled = false // not technically needed as cross tenant replication not supported when is_hns_enabled = true
  tags                             = local.tre_workspace_tags

  dynamic "identity" {
    for_each = var.enable_cmk_encryption ? [1] : []
    content {
      type         = "UserAssigned"
      identity_ids = [azurerm_user_assigned_identity.encryption_identity[0].id]
    }
  }

  dynamic "customer_managed_key" {
    for_each = var.enable_cmk_encryption ? [1] : []
    content {
      key_vault_key_id          = azurerm_key_vault_key.encryption_key[0].versionless_id
      user_assigned_identity_id = azurerm_user_assigned_identity.encryption_identity[0].id
    }
  }

  # changing this value is destructive, hence attribute is in lifecycle.ignore_changes block below
  infrastructure_encryption_enabled = true

  lifecycle { ignore_changes = [infrastructure_encryption_enabled, tags] }

  blob_properties {
    delete_retention_policy {
      days = 7
    }
    container_delete_retention_policy {
      days = 7
    }
  }

  share_properties {
    retention_policy {
      days = 7
    }
  }
}


# Using AzAPI as AzureRM uses shared account key for Azure files operations
resource "azapi_resource" "shared_storage" {
  type      = "Microsoft.Storage/storageAccounts/fileServices/shares@2023-05-01"
  name      = local.shared_storage_name
  parent_id = "${azurerm_storage_account.stg.id}/fileServices/default"
  body = {
    properties = {
      shareQuota       = var.shared_storage_quota
      enabledProtocols = "SMB"
    }
  }

  depends_on = [
    azurerm_private_endpoint.stgfilepe,
    azurerm_storage_account_network_rules.stgrules
  ]
}

resource "azurerm_storage_container" "stgcontainer" {
  name                  = "datalake"
  storage_account_id    = azurerm_storage_account.stg.id
  container_access_type = "private"

  depends_on = [
    azurerm_private_endpoint.stgblobpe,
    azurerm_storage_account_network_rules.stgrules
  ]
}

resource "azurerm_storage_account_network_rules" "stgrules" {
  storage_account_id = azurerm_storage_account.stg.id

  # When deploying from a local machine we need to "allow"
  default_action = var.enable_local_debugging ? "Allow" : "Deny"
  bypass         = ["AzureServices"]
}

resource "azurerm_private_endpoint" "stgfilepe" {
  name                = "stgfilepe-${local.workspace_resource_name_suffix}"
  location            = azurerm_resource_group.ws.location
  resource_group_name = azurerm_resource_group.ws.name
  subnet_id           = module.network.services_subnet_id
  tags                = local.tre_workspace_tags

  depends_on = [
    module.network
  ]

  lifecycle { ignore_changes = [tags] }

  private_dns_zone_group {
    name                 = "private-dns-zone-group"
    private_dns_zone_ids = [module.network.filecore_zone_id]
  }

  private_service_connection {
    name                           = "stgfilepesc-${local.workspace_resource_name_suffix}"
    private_connection_resource_id = azurerm_storage_account.stg.id
    is_manual_connection           = false
    subresource_names              = ["File"]
  }
}

resource "azurerm_private_endpoint" "stgblobpe" {
  name                = "stgblobpe-${local.workspace_resource_name_suffix}"
  location            = azurerm_resource_group.ws.location
  resource_group_name = azurerm_resource_group.ws.name
  subnet_id           = module.network.services_subnet_id
  tags                = local.tre_workspace_tags

  depends_on = [
    module.network,
    azurerm_private_endpoint.stgfilepe
  ]

  lifecycle { ignore_changes = [tags] }

  private_dns_zone_group {
    name                 = "private-dns-zone-group"
    private_dns_zone_ids = [module.network.blobcore_zone_id]
  }

  private_service_connection {
    name                           = "stgblobpesc-${local.workspace_resource_name_suffix}"
    private_connection_resource_id = azurerm_storage_account.stg.id
    is_manual_connection           = false
    subresource_names              = ["Blob"]
  }
}

resource "azurerm_private_endpoint" "stgdfspe" {
  name                = "stgdfspe-${local.workspace_resource_name_suffix}"
  location            = azurerm_resource_group.ws.location
  resource_group_name = azurerm_resource_group.ws.name
  subnet_id           = module.network.services_subnet_id
  tags                = local.tre_workspace_tags

  depends_on = [
    module.network,
    azurerm_private_endpoint.stgblobpe
  ]

  lifecycle { ignore_changes = [tags] }

  private_dns_zone_group {
    name                 = "private-dns-zone-group"
    private_dns_zone_ids = [module.network.dfscore_zone_id]
  }

  private_service_connection {
    name                           = "stgdfspesc-${local.workspace_resource_name_suffix}"
    private_connection_resource_id = azurerm_storage_account.stg.id
    is_manual_connection           = false
    subresource_names              = ["dfs"]
  }
}

# Azure Backup can fail the first storage registrations in a new vault with CloudInternalError.
# This step tries up to five times and removes the first registration that succeeds. Then the
# registration below is not the first one, and Terraform creates and owns the registration.
resource "terraform_data" "backup_registration_warm_up" {
  count = var.enable_backup ? 1 : 0

  input = {
    container_url      = "https://management.azure.com${module.backup[0].vault_id}/backupFabrics/Azure/protectionContainers/StorageContainer;storage;${azurerm_resource_group.ws.name};${azurerm_storage_account.stg.name}?api-version=2023-04-01"
    storage_account_id = azurerm_storage_account.stg.id
    subscription_id    = data.azurerm_client_config.current.subscription_id
  }

  provisioner "local-exec" {
    interpreter = ["/bin/bash", "-c"]
    command     = <<EOT
set -euo pipefail
az login --identity --output none
az account set --subscription "${self.input.subscription_id}"
url="${self.input.container_url}"
if az rest --method get --url "$url" --output none 2>/dev/null; then
  echo "The storage account is already registered with the vault"
  exit 0
fi
body='{"properties":{"backupManagementType":"AzureStorage","containerType":"StorageContainer","sourceResourceId":"${self.input.storage_account_id}"}}'
for try in 1 2 3 4 5; do
  if [ "$try" -gt 1 ]; then
    sleep 60
  fi
  operation=$(az rest --method put --url "$url" --body "$body" --debug 2>&1 | sed -n "s/.*'Azure-AsyncOperation': '\([^']*\)'.*/\1/p" | head -n 1 || true)
  status=Unknown
  if [ -n "$operation" ]; then
    for attempt in $(seq 1 60); do
      status=$(az rest --method get --url "$operation" --query status --output tsv 2>/dev/null || echo Unknown)
      [ "$status" = "InProgress" ] || break
      sleep 10
    done
  else
    sleep 120
  fi
  echo "Registration attempt $try ended with status $status"
  if az rest --method get --url "$url" --output none 2>/dev/null; then
    # Remove the registration, so that Terraform creates and owns the registration.
    az rest --method delete --url "$url" --output none
    for attempt in $(seq 1 60); do
      az rest --method get --url "$url" --output none 2>/dev/null || exit 0
      sleep 10
    done
    echo "The storage account is still registered with the vault after 10 minutes" >&2
    exit 1
  fi
done
EOT
  }
}

resource "azurerm_backup_container_storage_account" "storage_account" {
  count               = var.enable_backup ? 1 : 0
  resource_group_name = azurerm_resource_group.ws.name
  recovery_vault_name = module.backup[0].vault_name
  storage_account_id  = azurerm_storage_account.stg.id

  depends_on = [
    terraform_data.backup_registration_warm_up
  ]
}

resource "terraform_data" "wait_for_backup_cleanup" {
  count = var.enable_backup ? 1 : 0

  input = {
    storage_account_id = "/subscriptions/${data.azurerm_client_config.current.subscription_id}/resourceGroups/${azurerm_resource_group.ws.name}/providers/Microsoft.Storage/storageAccounts/${azurerm_storage_account.stg.name}"
    subscription_id    = data.azurerm_client_config.current.subscription_id
  }

  provisioner "local-exec" {
    when        = destroy
    interpreter = ["/bin/bash", "-c"]
    command     = <<EOT
set -euo pipefail
az login --identity
az account set --subscription "${self.input.subscription_id}"
echo "Checking for backup locks on storage account..."
for attempt in 1 2 3 4 5; do
  locks=$(az lock list --resource "${self.input.storage_account_id}" --query '[].id' -o tsv)
  if [ -z "$locks" ]; then
    echo "No locks found on storage account"
    sleep 30
    exit 0
  else
    echo "Attempt $attempt: Found locks, waiting for removal..."
    echo "$locks"
    if [ "$attempt" -lt 5 ]; then
      sleep 60
    else
      echo "Warning: Locks still present after 5 attempts, proceeding anyway"
      exit 0
    fi
  fi
done
EOT
  }

  depends_on = [
    azurerm_storage_container.stgcontainer,
    azapi_resource.shared_storage,
    azurerm_private_endpoint.stgdfspe,
    azurerm_private_endpoint.stgblobpe,
    azurerm_private_endpoint.stgfilepe

  ]
}

resource "azurerm_backup_protected_file_share" "file_share" {
  count                     = var.enable_backup ? 1 : 0
  resource_group_name       = azurerm_resource_group.ws.name
  recovery_vault_name       = module.backup[0].vault_name
  source_storage_account_id = azurerm_storage_account.stg.id
  source_file_share_name    = azapi_resource.shared_storage.name
  backup_policy_id          = module.backup[0].fileshare_backup_policy_id

  depends_on = [
    azurerm_backup_container_storage_account.storage_account,
    azapi_resource.shared_storage,
    azurerm_private_endpoint.stgfilepe
  ]
}
