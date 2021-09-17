# Azure Machine Learning Service bundle

See: [https://azure.microsoft.com/services/machine-learning/](https://azure.microsoft.com/services/machine-learning/)

This service installs the following resources into an existing virtual network within the workspace:

![Azure Machine Learning Service](images/aml_service.png)

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

## Prerequisites

- [A base workspace bundle installed](../../../templates/workspaces/base)

## Manual Deployment

1. Create a copy of `templates/workspace_services/azureml/.env.sample` with the name `.env` and update the variables with the appropriate values.

  | Environment variable name | Description |
  | ------------------------- | ----------- |
  | `WORKSPACE_ID` | The 4 character unique identifier used when deploying the base workspace bundle. |

1. Build and install the Azure ML Service bundle

  ```cmd
  make porter-build DIR=./templates/workspace_services/azureml
  make porter-install DIR=./templates/workspace_services/azureml
  ```
