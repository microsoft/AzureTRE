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

### Properties

| Property | Options | Description |
| -------- | ------- | ----------- |
| `client_id` | Valid client ID of a pre-created Workspace App Registration. | Optional. Provide this to reuse an existing application. Leave empty (default) to allow the TRE to create and manage the workspace application automatically. |

!!! note
    When `client_id` is provided, Terraform imports and manages the application (including its secret), so the application is **deleted when the workspace is uninstalled**. Leave `client_id` empty to have the TRE create and manage a dedicated application for the workspace.

## Backup

When `enable_backup` is set (the default) the base workspace deploys a Recovery Services Vault into the workspace resource group and protects the workspace's shared storage (and any VMs configured for backup).

| `delete_backups_on_uninstall` | Behaviour on workspace deletion |
| ----------------------------- | ------------------------------- |
| `false` (default) | **Retain the backups.** Protection is stopped but the recovery points are kept. The vault, its backup resources and the workspace resource group are removed from the Terraform state, so the **resource group is retained and continues to hold the Recovery Services Vault and its recovery points** after the workspace is deleted. |
| `true` | **Delete the backups.** Protection is stopped with data deletion, the backup containers are unregistered and the Recovery Services Vault (with its recovery points) is deleted. Terraform then destroys the rest of the workspace, including its resource group, leaving nothing behind. |

Both flags are updateable, so the choice can be changed on an existing workspace before it is deleted.

> **Note:** If [vault immutability](https://learn.microsoft.com/azure/backup/backup-azure-immutable-vault-concept) is enabled on the Recovery Services Vault (for example, enforced by an Azure Policy in your environment), backups cannot be deleted before they expire. In this case `delete_backups_on_uninstall = true` will not be able to remove the backups or vault, and workspace deletion may fail.

## Azure Trusted Services
*Azure Trusted Services* are allowed to connect to both the key vault and storage account provisioned within the workspace. If this is undesirable additional resources without this setting configured could be deployed by a custom workspace.

Further details around which Azure services are allowed to connect can be found below:

- Key Vault: <https://docs.microsoft.com/en-us/azure/key-vault/general/overview-vnet-service-endpoints#trusted-services>
- Azure Storage: <https://docs.microsoft.com/en-us/azure/storage/common/storage-network-security?msclkid=ee4e79e4b97911eca46dae54da464d11&tabs=azure-portal#trusted-access-for-resources-registered-in-your-subscription>

## Client secret management
The workspace application password is created with a default validity of approximately 2 years. The secret is stored in the workspace Key Vault as `workspace-client-secret` (with the client ID stored as `workspace-client-id`).

Workspaces should be upgraded periodically (at least every 2 years) to refresh the password.
