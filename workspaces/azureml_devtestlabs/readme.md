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
    `make workspaces-vanilla-porter-build`
    `make workspaces-vanilla-porter-publish`

- A Azure ML Service bundle published
    `make services-azureml-porter-build`  
    `make services-azureml-porter-publish`

- A DevTest Labs Service bundle published
    `make services-devtestlabs-porter-build`  
    `make services-devtestlabs-porter-publish`

- A Azure ML DevTest Labs Workspace bundle built
    `make services-devtestlabs-porter-build`

## To deploy

- Once prerequisites are installed, create a copy of `workspaces/azureml_devtestlabs/.env.sample` called `.env` in the  `workspaces/azureml_devtestlabs/` directory. Update the environment variable values to match your installation.

- Run: `make workspaces-azureml_devtestlabs-porter-install`
