# Pre-deployment steps

!!! info
    See [Environment variables](../environment-variables.md) for full details of the deployment related variables.

## Set environment configuration variables of shared management resources

1. Open the `/devops/.env.sample` file and then save it without the .sample extension. You should now have a file called `.env` located in the `/devops` folder. The file contains configuration variables for the shared management infrastructure which is used to support the deployment of one or more Azure TRE instances.

2. Provide the values for the following variables:

  | Variable | Description |
  | -------- | ----------- |
  | `LOCATION` | The [Azure location (region)](https://azure.microsoft.com/global-infrastructure/geographies/#geographies) for all resources. E.g., `westeurope` |
  | `MGMT_RESOURCE_GROUP_NAME` | The shared resource group for all management resources, including the storage account. |
  | `MGMT_STORAGE_ACCOUNT_NAME` | The name of the storage account to hold the Terraform state and other deployment artifacts. |
  | `ACR_NAME` | A globally unique name for the [Azure Container Registry (ACR)](https://docs.microsoft.com/azure/container-registry/) that will be created to store deployment images. |
  | `ARM_SUBSCRIPTION_ID` | The Azure subscription ID for all resources. |

  !!! tip
      To retrieve your Azure subscription ID, use the `az` command line interface available in the development container. In the terminal window in Visual Studio Code, type `az login` followed by `az account show` to see your default subscription. Please refer to `az account -help` for further details on how to change your active subscription.

The rest of the variables can have their default values. You should now have a `.env` file that looks similar to the one below:

```plaintext
# Management infrastructure
LOCATION=westeurope
MGMT_RESOURCE_GROUP_NAME=aztremgmt
MGMT_STORAGE_ACCOUNT_NAME=aztremgmt
TERRAFORM_STATE_CONTAINER_NAME=tfstate
ACR_NAME=aztreacr

ARM_SUBSCRIPTION_ID=12...54e

# If you want to override the currently signed in credentials
# ARM_TENANT_ID=__CHANGE_ME__
# ARM_CLIENT_ID=__CHANGE_ME__
# ARM_CLIENT_SECRET=__CHANGE_ME__

# Debug mode
DEBUG="false"
```

  3. If you want to disable the built-in web UI (`./ui`) ensure you set `DEPLOY_UI=false` in the /templates/core/.env file.

## Next steps

* [Deploying Azure TRE](manual-deployment.md)
