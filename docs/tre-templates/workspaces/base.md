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

## Blocked Azure resource types

Base workspace `2.12.0` adds the updateable `blocked_resource_types` setting.
It defaults to `[]`, which creates no policy assignment and preserves existing deployment behaviour.
Set the list when creating or updating a workspace through TRE. For example:

```json
{
  "blocked_resource_types": ["Microsoft.Bing/accounts"]
}
```

This example denies creation and updates of all Bing account kinds in this workspace's resource group.
The workspace assigns the built-in **Not allowed resource types** policy with effect `Deny` and enforcement enabled.
The assignment uses the workspace subscription, including when it differs from the core subscription.
Multiple exact resource types can be listed. Wildcards and resource IDs are not accepted.
Do not block resource types required by the workspace or its services: that can prevent installation and upgrades.

The deployment identity needs permission to manage Azure Policy assignments at the workspace resource group when this option is used.
The template does not grant itself that permission or create a custom policy definition.
An administrator can grant the required policy-assignment permissions at the narrowest applicable scope.

The policy belongs to the workspace, not to an individual Foundry service.
Changing the list updates the assignment. Clearing the list removes it. Deleting a workspace also removes its assignment.
Deleting a Foundry service does not change it. Inherited policy assignments remain effective.
Workspace Owners who can change workspace settings can change this list. Use administrator-owned inherited policies for mandatory restrictions.

For direct Porter use, `blocked_resource_types` is a base64-encoded JSON array, following the existing complex-parameter convention.
The default is `W10=`. The local parameter-set environment variable is `BLOCKED_RESOURCE_TYPES`.
The TRE API accepts an ordinary JSON array and the resource processor performs the encoding.

A [Deny policy](https://learn.microsoft.com/en-us/azure/governance/policy/concepts/effect-deny) does not disable existing resources or revoke their credentials.
It does not block data-plane calls or resources in other resource groups or subscriptions.
For Foundry, Bing resource policy, web-search registration and remote MCP restrictions are [separate controls](../workspace-services/ai-foundry.md#hosted-tool-controls).

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
