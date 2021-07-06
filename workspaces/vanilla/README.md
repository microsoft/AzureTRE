# Azure TRE vanilla workspace

## Prerequisites

- A TRE environment

## Manual Deployment

1. Create a copy of `/workspaces/vanilla/.env.sample` with the name `.env` and update the variables with the appropriate values.

| Environment variable name | Description |
| ------------------------- | ----------- |
| `WORKSPACE_ID` | A 4 ter unique identifier for the workspace for this TRE. `WORKSPACE_ID` can be found in the resource names of the workspace resources; for example, a `WORKSPACE_ID` of `ab12` will result in a resource group name for workspace of `rg-<tre-id>-ab12`. Allowed characters: Alphanumeric. |
| `ADDRESS_SPACE` | The address space for the workspace virtual network. For example `192.168.1.0/24`|

1. Build and deploy the vanilla workspace
    - `make porter-build DIR=./workspaces/vanilla`  
    - `make porter-install DIR=./workspaces/vanilla`
