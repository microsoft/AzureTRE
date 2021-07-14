# Azure machine Learning Service bundle

See: [https://azure.microsoft.com/services/machine-learning/](https://azure.microsoft.com/services/machine-learning/)

## Firewall Rules

Please be aware that the following Firewall rules are opened for the workspace when this service is deployed:

URLs:

- graph.windows.net
- ml.azure.com
- login.microsoftonline.com
- aadcdn.msftauth.net
- graph.microsoft.com
- management.azure.com
- viennaglobal.azurecr.io

Service Tags:

- Storage.`{AzureRegion}`
- AzureContainerRegistry

## Manual Deployment

1. Prerequisites for deployment:
    - [A vanilla workspace bundle installed](../../vanilla)

1. Create a copy of `workspaces/services/azureml/.env.sample` with the name `.env` and update the variables with the appropriate values.

| Environment variable name | Description |
| ------------------------- | ----------- |
| `WORKSPACE_ID` | The 4 character unique identifier used when deploying the vanilla workspace bundle. |

1. Build and install the Azure DevTest Labs Service bundle
    - `make porter-build DIR=./workspaces/services/azureml`  
    - `make porter-install DIR=./workspaces/services/azureml`
