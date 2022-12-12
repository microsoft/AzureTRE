# Pre-deployment steps

!!! info
    See [Environment variables](../environment-variables.md) for full details of the deployment related variables.

## Set environment configuration variables of shared management resources

1. In this part we will setup configuration variables in `config.yaml` file for the shared management infrastructure which is used to support the deployment of one or more Azure TRE instances.

2. Provide the values for the following variables:

  | Variable | Description |
  | -------- | ----------- |
  | `location` | The [Azure location (region)](https://azure.microsoft.com/global-infrastructure/geographies/#geographies) for all resources. E.g., `westeurope` |
  | `mgmt_resource_group_name` | The shared resource group for all management resources, including the storage account. |
  | `mgmt_storage_account_name` | The name of the storage account to hold the Terraform state and other deployment artifacts. |
  | `acr_name` | A globally unique name for the [Azure Container Registry (ACR)](https://docs.microsoft.com/azure/container-registry/) that will be created to store deployment images. |
  | `arm_subscription_id` | The Azure subscription ID for all resources. |

  !!! tip
      To retrieve your Azure subscription ID, use the `az` command line interface available in the development container. In the terminal window in Visual Studio Code, type `az login` followed by `az account show` to see your default subscription. Please refer to `az account -help` for further details on how to change your active subscription.

The rest of the variables can have their default values. You should now have a management section in the `config.yaml` file that looks similar to the one below:

```plaintext
  management:
    location: westeurope
    mgmt_resource_group_name: aztremgmt
    mgmt_storage_account_name: aztremgmt
    terraform_state_container_name: tfstate
    acr_name: aztreacr
    # Azure Resource Manager credentials used for CI/CD pipelines
    arm_subscription_id: 12...54e
    # If you want to override the currently signed in credentials
    # You would do this if running commands like `make terraform-install DIR=./templates/workspaces/base`
    # arm_tenant_id: __CHANGE_ME__
    # arm_client_id: __CHANGE_ME__
    # arm_client_secret: __CHANGE_ME__
```

  3. If you want to disable the built-in web UI (`./ui`) ensure you set `deploy_ui=false` under tre defaults section in the `config.yaml` file.

## Next steps

* [Deploying Azure TRE](manual-deployment.md)
