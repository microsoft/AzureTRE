# GitHub Actions workflows (CI/CD)

To deploy the Azure TRE using GitHub workflows, create a fork of the repository.

Deployment is done using the `/.github/workflows/deploy_tre.yml` workflow. This method is also used to deploy the dev/test environment for the original Azure TRE repository.

## Setup instructions

Before you can run the `deploy_tre.yml` workflow there are some one-time configuration steps that we need to do, similar to the Pre-deployment steps for manual deployment.

!!! tip
    In some of the steps below, you are asked to configure repository secrets. Follow the [GitHub guide](https://docs.github.com/en/actions/security-guides/encrypted-secrets) on creating repository secrets if you are unfamiliar with this step.

1. Create a service principal for the subscription so that the workflow can provision Azure resources.
1. Decide on a TRE ID and the location for the Azure resources
1. Create app registrations for API authentication
1. Create app registrations and a user for the E2E tests
1. Create a workspace app registration for setting up workspaces (for the E2E tests)
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

  Configure the service principal to trust GitHub Actions OIDC tokens from your repository:

  ```cmd
  az ad app federated-credential create --id <APPLICATION_OBJECT_ID> --parameters credential.json
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

1. Configure repository variables for OIDC authentication

  Configure the following **variables** (not secrets) in your repository or environment:

  | <div style="width: 230px">Variable name</div> | Description |
  | ----------- | ----------- |
  | `AZURE_CLIENT_ID` | The application (client) ID of the service principal created above |
  | `AZURE_TENANT_ID` | The tenant ID where the service principal was created |
  | `AZURE_SUBSCRIPTION_ID` | The Azure subscription ID where resources will be deployed |
  | `AZURE_ENVIRONMENT` | Optional. The Azure cloud environment. Default is `AzureCloud`. Use `AzureUSGovernment` for US Government cloud |

### Decide on a TRE ID and Azure resources location

Configure the TRE ID and LOCATION repository secrets

| <div style="width: 230px">Secret name</div> | Description |
| ----------- | ----------- |
| `TRE_ID` | A globally unique identifier. `TRE_ID` can be found in the resource names of the Azure TRE instance; for example, a `TRE_ID` of `tre-dev-42` will result in a resource group name for Azure TRE instance of `rg-tre-dev-42`. This must be less than 12 characters. Allowed characters: lowercase alphanumerics. |
| `LOCATION` | The Azure location (region) for all resources. E.g. `westeurope` |

### Create app registrations for API authentication

Follow the instructions to run the **app registration script** in the [Authentication and Authorization document](../auth.md#app-registrations). Use the values for TRE ID and LOCATION from above.

Configure the TRE API and Swagger UI repository secrets

| <div style="width: 230px">Secret name</div> | Description |
| ----------- | ----------- |
| `AAD_TENANT_ID` | The tenant ID of the Microsoft Entra ID. |
| `SWAGGER_UI_CLIENT_ID` | The application (client) ID of the TRE Swagger UI app. |
| `API_CLIENT_ID` | The application (client) ID of the TRE API app. |
| `API_CLIENT_SECRET` | The application password (client secret) of the TRE API app. |

### Create an app registration and a user for the E2E tests

Follow the instructions to [create an app registration and a test user for the E2E tests in the Authentication and Authorization](../auth.md#tre-e2e-test) document.

Configure the E2E Test repository secrets

| <div style="width: 230px">Secret name</div> | Description |
| ----------- | ----------- |
| `TEST_APP_ID` | The application (client) ID of the E2E Test app |
| `TEST_USER_NAME` | The username of the E2E Test User |
| `TEST_USER_PASSWORD` | The password of the E2E Test User |

### Create a workspace app registration for setting up workspaces (for the E2E tests)

Follow the [instructions to create a workspace app registration](../auth.md#workspaces) (used for the E2E tests) - and make the E2E test user a **WorkspaceOwner** for the app registration.

Configure the TEST_WORKSPACE_APP_ID repository secret

| <div style="width: 230px">Secret name</div> | Description |
| ----------- | ----------- |
| `TEST_WORKSPACE_APP_ID` | The application (client) ID of the Workspaces app. |
| `TEST_WORKSPACE_APP_SECRET` | The application (client) secret of the Workspaces app. |

### Configure repository/environment secrets

Configure additional secrets used in the deployment workflow:

| <div style="width: 230px">Secret name</div> | Description |
| ----------- | ----------- |
| `TRE_ID` | A globally unique identifier. `TRE_ID` can be found in the resource names of the Azure TRE instance; for example, a `TRE_ID` of `tre-dev-42` will result in a resource group name for Azure TRE instance of `rg-tre-dev-42`. This must be less than 12 characters. Allowed characters: lowercase alphanumerics. |
| `MGMT_RESOURCE_GROUP_NAME` | The name of the shared resource group for all Azure TRE core resources. |
| `MGMT_STORAGE_ACCOUNT_NAME` | The name of the storage account to hold the Terraform state and other deployment artifacts. E.g. `mystorageaccount`. |
| `ACR_NAME` | A globally unique name for the Azure Container Registry (ACR) that will be created to store deployment images. |
| `CUSTOM_DOMAIN` | Optional. Custom domain name to access the Azure TRE portal. See [Custom domain name](../custom-domain.md). |


### Configure repository/environment variables

Configure variables used in the deployment workflow:

| <div style="width: 230px">Variable name</div> | Description |
| ----------- | ----------- |
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
| `ENABLE_CMK_ENCRYPTION` | Optional. Default is `false`, if set to `true` customer-managed key encryption will be enabled for all supported resources. |

### Deploy the TRE using the workflow

With all the repository secrets set, you can trigger a workflow run by pushing to develop/main of your fork, or by dispatching the workflow manually.
