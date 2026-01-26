# Pre-deployment steps

## Setup Github Environment

The workflows are using Github environment to source its environment variables. Follow [this guide](https://docs.github.com/en/actions/deployment/targeting-different-environments/using-environments-for-deployment#creating-an-environment) to define it in your github repository and provide it as an input for the workflows.


## GitHub Actions workflows (CI/CD)

Deployment is done using the `/.github/workflows/deploy_tre.yml` workflow. This method is also used to deploy the dev/test environment for the original Azure TRE repository.

## Setup instructions

Before you can run the `deploy_tre.yml` workflow there are some one-time configuration steps that we need to do, similar to the Pre-deployment steps for manual deployment.

1. Create a service principal for the subscription so that the workflow can provision Azure resources.
1. Decide on a TRE ID and the location for the Azure resources
1. Configure repository secrets
1. Deploy the TRE using the workflow

### Create a service principal and configure OIDC authentication

1. Login to Azure

  Log in to Azure using `az login` and select the Azure subscription you wish to deploy Azure TRE to:

  ```cmd
  az login
  az account list
  az account set --subscription <subscription ID>
  ```

  See [Sign in with Azure CLI](https://docs.microsoft.com/cli/azure/authenticate-azure-cli) for more details.

1. Create a service principal

  A service principal needs to be created to authorize CI/CD workflows to provision resources for the TRE workspaces and workspace services.

  Create a main service principal with "**Owner**" role:

  ```cmd
  az ad sp create-for-rbac --name "sp-aztre-cicd" --role Owner --scopes /subscriptions/<subscription_id>
  ```

  !!! caution
      Save the output (especially the `appId` and `tenant`) - you will need it for the next steps

1. Configure federated identity credentials for GitHub Actions OIDC

  Configure the service principal to trust GitHub Actions OIDC tokens from your repository. The `--id` parameter expects the `appId` (application/client ID) returned from the previous step:

  ```cmd
  az ad app federated-credential create --id <appId> --parameters credential.json
  ```

  Where `credential.json` contains (replace `OWNER`, `REPO`, and `ENVIRONMENT` with your values):

  ```json
  {
    "name": "GitHubActions",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:OWNER/REPO:environment:ENVIRONMENT",
    "description": "GitHub Actions OIDC for Azure TRE",
    "audiences": [
      "api://AzureADTokenExchange"
    ]
  }
  ```

  For the main/develop branches, you may also want to add federated credentials with subject `repo:OWNER/REPO:ref:refs/heads/main` and `repo:OWNER/REPO:ref:refs/heads/develop`.

  See [Configure a federated identity credential on an app](https://learn.microsoft.com/entra/workload-id/workload-identity-federation-create-trust?pivots=identity-wif-apps-methods-azcli) for more details.

### Configure Core Secrets

Configure the following secrets in your github environment:

| <div style="width: 230px">Secret name</div> | Description |
| ----------- | ----------- |
| `TRE_ID` | A globally unique identifier. `TRE_ID` can be found in the resource names of the Azure TRE instance; for example, a `TRE_ID` of `tre-dev-42` will result in a resource group name for Azure TRE instance of `rg-tre-dev-42`. This must be less than 12 characters. Allowed characters: lowercase alphanumerics. |
| `MGMT_RESOURCE_GROUP_NAME` | The name of the shared resource group for all Azure TRE core resources. |
| `MGMT_STORAGE_ACCOUNT_NAME` | The name of the storage account to hold the Terraform state and other deployment artifacts. E.g. `mystorageaccount`. |
| `ACR_NAME` | A globally unique name for the Azure Container Registry (ACR) that will be created to store deployment images. |
| `EXTERNAL_KEY_STORE_ID` | Optional. The ID of the external Key Vault to store CMKs in. Should not be set if `ENCRYPTION_KV_NAME` is set and only required if `ENABLE_CMK_ENCRYPTION` is true. |
| `ENCRYPTION_KV_NAME` | Optional. The name of the Key Vault for encryption keys. Should not be set if `EXTERNAL_KEY_STORE_ID` is set and only required if `ENABLE_CMK_ENCRYPTION` is true. |
| `AZURE_CLIENT_ID` | The application (client) ID of the service principal created above |
| `AZURE_TENANT_ID` | The tenant ID where the service principal was created |
| `AZURE_SUBSCRIPTION_ID` | The Azure subscription ID where resources will be deployed |

### Configure Core Variables

Configure the following **variables** in your github environment:

| <div style="width: 230px">Variable name</div> | Description |
| ----------- | ----------- |
| `AZURE_ENVIRONMENT` | Optional. The Azure cloud environment. Default is `AzureCloud`. Use `AzureUSGovernment` for US Government cloud |
| `LOCATION` | The Azure location (region) for all resources. E.g. `westeurope` |
| `TERRAFORM_STATE_CONTAINER_NAME` | Optional. The name of the blob container to hold the Terraform state. Default value is `tfstate`. |
| `CORE_ADDRESS_SPACE` | Optional. The address space for the Azure TRE core virtual network. Default value is `10.0.0.0/22`. |
| `TRE_ADDRESS_SPACE` | Optional. The address space for the whole TRE environment virtual network where workspaces networks will be created (can include the core network as well). Default value is `10.0.0.0/16` |
| `CORE_APP_SERVICE_PLAN_SKU` | Optional. The SKU used for AppService plan for core infrastructure. Default value is `P1v2`. |
| `WORKSPACE_APP_SERVICE_PLAN_SKU` | Optional. The SKU used for AppService plan used in E2E tests. Default value is `P1v2`. |
| `RESOURCE_PROCESSOR_NUMBER_PROCESSES_PER_INSTANCE` | Optional. The number of processes to instantiate when the Resource Processor starts. Equates to the number of parallel deployment operations possible in your TRE. Defaults to `5`. |
| `ENABLE_SWAGGER` | Optional. Determines whether the Swagger interface for the API will be available. Default value is `false`. |
| `FIREWALL_SKU` | Optional. The SKU of the Azure Firewall instance. Default value is `Standard`. Allowed values [`Basic`, `Standard`, `Premium`]. See [Azure Firewall SKU feature comparison](https://learn.microsoft.com/en-us/azure/firewall/choose-firewall-sku). |
| `APP_GATEWAY_SKU` | Optional. The SKU of the Application Gateway. Default value is `Standard_v2`. Allowed values [`Standard_v2`, `WAF_v2`] |
| `CUSTOM_DOMAIN` | Optional. Custom domain name to access the Azure TRE portal. See [Custom domain name](../custom-domain.md). |
| `ENABLE_CMK_ENCRYPTION` | Optional. Default is `false`, if set to `true` customer-managed key encryption will be enabled for all supported resources. |

### Configure Authentication Secrets

In a previous [Setup Auth configuration](./setup-auth-entities.md) step authentication configuration was added in `config.yaml` file. Go to this file and add those env vars to your github environment:

  | Secret Name | Description |
  | -------- | ----------- |
  | `AAD_TENANT_ID` | Tenant id against which auth is performed. |
  | `APPLICATION_ADMIN_CLIENT_ID` | This client will administer Microsoft Entra ID Applications for TRE |
  | `APPLICATION_ADMIN_CLIENT_SECRET` | This client will administer Microsoft Entra ID Applications for TRE |
  | `TEST_ACCOUNT_CLIENT_ID` | This will be created by default, but can be disabled by editing `/devops/scripts/create_aad_assets.sh`. This is the user that will run the tests for you |
  | `TEST_ACCOUNT_CLIENT_SECRET` | This will be created by default, but can be disabled by editing `/devops/scripts/create_aad_assets.sh`. This is the user that will run the tests for you |
  | `API_CLIENT_ID` | API application (client) ID. |
  | `API_CLIENT_SECRET` | API application client secret. |
  | `SWAGGER_UI_CLIENT_ID` | Swagger (OpenAPI) UI application (client) ID. |
  | `TEST_WORKSPACE_APP_ID` | Each workspace is secured behind it's own AD Application. Use the value of `WORKSPACE_API_CLIENT_ID` created in the `/config.yaml` env file |
  | `TEST_WORKSPACE_APP_SECRET` | Each workspace is secured behind it's own AD Application. This is the secret for that application. Use the value of `WORKSPACE_API_CLIENT_SECRET` created in the `/config.yaml` env file |

!!! info
    See [Environment variables](../environment-variables.md) for full details of the deployment related variables.

### Setup Github env in workflow

In your repository you will find that the pipelines under the folder `.github/workflows` on top of each workflow there is the workflow inputs part where the used Github environment name is set, make sure to update it with yours, for example:

![Setup env in pipeline](../../assets/using-tre/pipelines_set_env.png)

### Deploy the TRE using the workflow

With all the repository secrets set, you can trigger a workflow run by pushing to develop/main of your repo, or by dispatching the workflow manually.

### Run CI/CD on Main Branch First

It is important to run the CI/CD pipeline on the main branch first. This will create an environment that represents the current main branch. It will also define the `CI_CACHE_ACR_NAME` used for caching.

## Next steps

* [Deploying Azure TRE in Pipelines](cicd-deployment.md)
