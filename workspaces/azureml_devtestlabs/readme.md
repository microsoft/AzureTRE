# Azure ML and Dev Test Labs Worksapce

This deploys a TRE workspace with the following services:

- [Azure ML](./services/azureml)
- [Azure Dev Test Labs](./services/devtestlabs)

Please follow the above links to learn more about how to access the services and any firewall rules that they will open in the workspace.

## Manual deployment

1. Publish the bundles required for this workspace:

- Vanilla Workspace
    `make porter-build DIR=./workspaces/vanilla`
    `make porter-publish DIR=./workspaces/vanilla`

- Azure ML Service
    `make porter-build DIR=./workspaces/services/azureml`  
    `make porter-publish DIR=./workspaces/services/azureml`

- DevTest Labs Service
    `make porter-build DIR=./workspaces/services/devtestlabs`  
    `make porter-publish DIR=./workspaces/services/devtestlabs`

1. Create a copy of `workspaces/azureml_devtestlabs/.env.sample` with the name `.env` and update the variables with the appropriate values.

| Environment variable name | Description |
| ------------------------- | ----------- |
| `WORKSPACE_ID` | A 4 character unique identifier for the workspace for this TRE. `WORKSPACE_ID` can be found in the resource names of the workspace resources; for example, a `WORKSPACE_ID` of `ab12` will result in a resource group name for workspace of `rg-<tre-id>-ab12`. Allowed characters: Alphanumeric. |
| `ADDRESS_SPACE` | The address space for the workspace virtual network. For example `192.168.1.0/24`|

1. Build and install the workspace:

    `make porter-publish DIR=./workspaces/azureml_devtestlabs`
    `make porter-install DIR=./workspaces/azureml_devtestlabs`
