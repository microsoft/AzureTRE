# Setup Auth configuration

Next, you will set the configuration variables for the specific Azure TRE instance:

1. Open the `/config.sample.yaml` file and then save it without the .sample extension. You should now have a file called `config.yaml` located in the root folder. The file contains configuration variables. In this part you will add the configuration required for the shared management infrastructure which is used to support the deployment of one or more Azure TRE instances.

1. Provide the values for the following variables under management section in your `config.yaml` file:

    | Variable | Description |
    | -------- | ----------- |
    | `location` | The [Azure location (region)](https://azure.microsoft.com/global-infrastructure/geographies/#geographies) for all resources. E.g., `westeurope` |
    | `mgmt_resource_group_name` | The shared resource group for all management resources, including the storage account. |
    | `mgmt_storage_account_name` | The name of the storage account to hold the Terraform state and other deployment artifacts. |
    | `acr_name` | A globally unique name for the [Azure Container Registry (ACR)](https://docs.microsoft.com/azure/container-registry/) that will be created to store deployment images. |
    | `arm_subscription_id` | The Azure subscription ID for all resources. |

    !!! tip
        To retrieve your Azure subscription ID, use the `az` command line interface available in the development container. In the terminal window in Visual Studio Code, type `az login` followed by `az account show` to see your default subscription. Please refer to `az account -help` for further details on how to change your active subscription.

    The rest of the variables can have their default values.

1. Decide on a name for your `tre_id` ID for the Azure TRE instance. The value will be used in various Azure resources and Microsoft Entra ID application names. It **needs to be globally unique and less than 12 characters in length**. Use **only** lowercase alphanumerics. Choose wisely!
1. Once you have decided on which AD Tenant paradigm, then you should be able to set `aad_tenant_id` in the authentication section in your `config.yaml` file.
1. Your Microsoft Entra ID Tenant Admin can now use the terminal window in Visual Studio Code to execute the following script from within the development container to create all the Microsoft Entra ID Applications that are used for TRE. The details of the script are covered in the [auth document](../auth.md).

   ```bash
   make auth
   ```
  !!! note
      Credentials created by the `make auth` command will be added under the authentication section in your `config.yaml` file

  !!! note
      In case you have several subscriptions and would like to change your default subscription use `az account set --subscription <desired subscription ID>`

  !!! note
      The full functionality of the script requires directory admin privileges. You may need to contact your friendly Microsoft Entra ID admin to complete this step. The app registrations can be created manually in Azure Portal too. For more information, see [Authentication and authorization](../auth.md).
  

All other variables can have their default values for now.

## Add admin user

Make sure the **TRE Administrators** and **TRE Users** roles, defined by the API app registration, are assigned to your user and others as required. See [Enabling users](../auth.md#enabling-users) for instructions.
