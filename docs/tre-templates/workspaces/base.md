# Azure TRE base workspace

The base workspace template is the foundation that all other workspaces and workspace services are built upon. Alternative workspace architectures could be used. However, the templates provided in this repository rely on the specific architecture of this base workspace.

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
| `client_id` | Valid client ID of the Workspace App Registration. | Required only when `auth_type` is set to `Manual`. Leave empty (default) to allow the TRE to create and manage the workspace application automatically. |

## Azure Trusted Services
*Azure Trusted Services* are allowed to connect to both the key vault and storage account provisioned within the workspace. If this is undesirable additional resources without this setting configured can be deployed.

Further details around which Azure services are allowed to connect can be found below:

- Key Vault: <https://docs.microsoft.com/en-us/azure/key-vault/general/overview-vnet-service-endpoints#trusted-services>
- Azure Storage: <https://docs.microsoft.com/en-us/azure/storage/common/storage-network-security?msclkid=ee4e79e4b97911eca46dae54da464d11&tabs=azure-portal#trusted-access-for-resources-registered-in-your-subscription>

## Client secret rotation
Two secrets (primary and secondary) are created, rotated every 30 days, and offset by 15 days so that one secret is always valid during rollover.
Each credential remains valid for 180 days, and the currently active secret is synced to the workspace key vault as `workspace-client-secret` (with the client ID stored as `workspace-client-id`).

Re-running the workspace deployment (for example as part of an upgrade) automatically refreshes the secret whenever the rotation schedule requires it—no manual input is needed.
