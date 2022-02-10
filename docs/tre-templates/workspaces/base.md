# Azure TRE base workspace

The base workspace template is the foundation that all other workspaces and workspace services are built upon. Alternative workspace architectures could be used. However, the templates provided in this repository rely on the specific architecture of this base workspace.

The base workspace template contains the following resources:

- Virtual Network
- Storage Account
- Key Vault
- VNet Peer to Core VNet
- Network Security Group

## Manual Deployment

!!! caution
    Resources should be deployed using the API (i.e. through the Swagger UI as described in the [setup instructions](../../tre-admins/setup-instructions/installing-base-workspace.md)). Only deploy manually for development/testing purposes.

1. Create a copy of `/templates/workspaces/base/.env.sample` with the name `.env` and update the variables with the appropriate values.

  | Environment variable name | Description |
  | ------------------------- | ----------- |
  | `ID` | A GUID to identify the workspace. The last 4 characters of this `ID` can be found in the resource names of the workspace resources; for example, a `ID` of `2e84dad0-9d4f-42bd-8e44-3d04095eab12` will result in a resource group name for workspace of `rg-<tre-id>-ab12`. |
  | `ADDRESS_SPACE` | The address space for the workspace virtual network, must be inside the `TRE_ADDRESS_SPACE` defined when deploying the TRE and not overlap with any other address spaces. |

1. Build and deploy the base workspace

  ```cmd
  make porter-build DIR=./templates/workspaces/base
  make porter-install DIR=./templates/workspaces/base
  ```
