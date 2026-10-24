# Azure TRE base workspace

The base workspace template is the foundation that all other workspaces and workspace services are built upon. Alternative workspace architectures could be used. However, the templates provided in this repository use the base workspace.

The base workspace template contains the following resources:

- Virtual Network
- Storage Account
- Key Vault
- VNet Peer to Core VNet
- Network Security Group
- App Service Plan

## Workspace Configuration

When deploying a workspace the following properties need to be configured.

### Required Properties

| Property | Options | Description |
| -------- | ------- | ----------- |
| `client_id` | Valid client ID of the Workspace App Registration. | The OpenID client ID which should be submitted to the OpenID service when necessary. This value is typically provided to you by the OpenID service when OpenID credentials are generated for your application. |
| `client_secret` | Valid client secret. | |

## Backup

When `enable_backup` is set (the default) the base workspace deploys a Recovery Services Vault into the workspace resource group and protects the workspace's shared storage (and any VMs configured for backup).

| `delete_backups_on_uninstall` | Behaviour on workspace deletion |
| ----------------------------- | ------------------------------- |
| `false` (default) | **Retain the backups.** Protection is stopped but the recovery points are kept. The vault, its backup resources and the workspace resource group are removed from the Terraform state, so the **resource group is retained and continues to hold the Recovery Services Vault and its recovery points** after the workspace is deleted. A file share recovery point is a snapshot in the workspace storage account, so the storage account, its share, its container and its network rules are also retained. With customer-managed keys, the encryption key, its identity and the role of that identity on the key store are retained too. |
| `true` | **Delete the backups.** Protection is stopped with data deletion, the backup containers are unregistered and the Recovery Services Vault (with its recovery points) is deleted. Azure Backup soft delete keeps a lease on the snapshots of the file shares after the vault delete, so the file shares are then deleted with their leased snapshots. This skips the soft delete retention of these snapshots. Terraform then destroys the rest of the workspace, including its resource group, leaving nothing behind. |

Both flags are updateable, so the choice can be changed on an existing workspace before it is deleted.

Before version 2.12.3, the retained path deleted the storage account and its share. The share delete failed with `DeleteShareWhenSnapshotLeased`, so the workspace stayed in `deleting_failed`.
To delete such a workspace, upgrade it to 2.12.3 or later, then delete it again.
The failed delete removed the resource group and the vault from the Terraform state, so the upgrade can end in `updating_failed` with an error that the resource group already exists.
The API keeps the new template version after a failed upgrade, so the next delete uses the corrected script.

Before version 2.12.3, the delete with `delete_backups_on_uninstall = true` failed with `DeleteShareWhenSnapshotLeased` after the vault delete, so the workspace stayed in `deleting_failed`.
To delete such a workspace, do these steps:

1. Delete the file share with its leased snapshots: `az rest --method delete --url "https://management.azure.com/subscriptions/<subscription ID>/resourceGroups/rg-<TRE ID>-ws-<short workspace ID>/providers/Microsoft.Storage/storageAccounts/stgws<short workspace ID>/fileServices/default/shares/vm-shared-storage?api-version=2023-05-01&\$include=leased-snapshots"`.
2. Delete the workspace again.

> **Note:** If [vault immutability](https://learn.microsoft.com/azure/backup/backup-azure-immutable-vault-concept) is enabled on the Recovery Services Vault (for example, enforced by an Azure Policy in your environment), backups cannot be deleted before they expire. In this case `delete_backups_on_uninstall = true` will not be able to remove the backups or vault, and workspace deletion may fail.

## Azure Trusted Services
*Azure Trusted Services* are allowed to connect to both the key vault and storage account provisioned within the workspace. If this is undesirable additional resources without this setting configured could be deployed by a custom workspace.

Further details around which Azure services are allowed to connect can be found below:

- Key Vault: <https://docs.microsoft.com/en-us/azure/key-vault/general/overview-vnet-service-endpoints#trusted-services>
- Azure Storage: <https://docs.microsoft.com/en-us/azure/storage/common/storage-network-security?msclkid=ee4e79e4b97911eca46dae54da464d11&tabs=azure-portal#trusted-access-for-resources-registered-in-your-subscription>
