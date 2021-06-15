# Azure ML Worksapce

This deploys a TRE workspace with a private Azure ML deployment.

## Firewall Rules

Please be aware that the following Firewall rules are opened for the workspace:

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

- A deployed TRE instance

- A Vanilla Workspace Bundle published
    `make porter-build DIR=./workspaces/vanilla`
    `make porter-publish DIR=./workspaces/vanilla`

- A Azure ML Service bundle published
    `make porter-build DIR=./workspaces/services/azureml`  
    `make porter-publish DIR=./workspaces/services/azureml`

- A DevTest Labs Service bundle published
    `make porter-build DIR=./workspaces/services/devtestlabs`  
    `make porter-publish DIR=./workspaces/services/devtestlabs`

- CNAB image built (contains azure driver)
    `make build-cnab-image`

- A Azure ML DevTest Labs Workspace bundle built
    `make porter-build DIR=./workspaces/azureml-devtestlabs`

## To deploy

- Once prerequisites are installed, create a copy of `workspaces/azureml_devtestlabs/.env.sample` called `.env` in the  `workspaces/azureml_devtestlabs/` directory. Update the environment variable values to match your installation.

- Run: `make porter-install DIR=./workspaces/azureml-devtestlabs`
