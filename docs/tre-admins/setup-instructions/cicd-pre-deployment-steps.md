# Pre-deployment steps

## Setup Github Environment

The workflows are using Github environment to source its environment variables. Follow [this guide](https://docs.github.com/en/actions/deployment/targeting-different-environments/using-environments-for-deployment#creating-an-environment) to define it in your github repository and provide it as an input for the workflows.


## GitHub Actions workflows (CI/CD)

Deployment is done using the `/.github/workflows/deploy_tre.yml` workflow. This method is also used to deploy the dev/test environment for the original Azure TRE repository.

## Setup instructions

Before you can run the `deploy_tre.yml` workflow there are some one-time configuration steps that we need to do, similar to the Pre-deployment steps for manual deployment.

1. Create a service principal for the subscription so that the workflow can provision Azure resources.
1. Decide on a TRE ID and the location for the Azure resources
1. Create a Teams WebHook for deployment notifications
1. Configure repository secrets
1. Deploy the TRE using the workflow

### Create a service principal for provisioning resources

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
  az ad sp create-for-rbac --name "sp-aztre-cicd" --role Owner --scopes /subscriptions/<subscription_id> --sdk-auth
  ```

  !!! caution
      Save the JSON output locally - as you will need it later for setting secrets in the build

1. Create a secret in your github environment named `AZURE_CREDENTIALS` and use the JSON output from the previous step as its value. Note it should look similar to this:
```json
{
  "clientId": "",
  "clientSecret": "",
  "subscriptionId": "",
  "tenantId": ""
}
```

### Configure Core Secrets

Configure the following secrets in your github environment -

| <div style="width: 230px">Secret name</div> | Description |
| ----------- | ----------- |
| `TRE_ID` | A globally unique identifier. `TRE_ID` can be found in the resource names of the Azure TRE instance; for example, a `TRE_ID` of `tre-dev-42` will result in a resource group name for Azure TRE instance of `rg-tre-dev-42`. This must be less than 12 characters. Allowed characters: Alphanumeric, underscores, and hyphens. |
| `LOCATION` | The Azure location (region) for all resources. E.g. `westeurope` |
| `MGMT_RESOURCE_GROUP_NAME` | The name of the shared resource group for all Azure TRE core resources. |
| `MGMT_STORAGE_ACCOUNT_NAME` | The name of the storage account to hold the Terraform state and other deployment artifacts. E.g. `mystorageaccount`. |
| `ACR_NAME` | A globally unique name for the Azure Container Registry (ACR) that will be created to store deployment images. |
| `CORE_ADDRESS_SPACE` |  The address space for the Azure TRE core virtual network. E.g. `10.1.0.0/22`. Recommended `/22` or larger.  |
| `TRE_ADDRESS_SPACE` | The address space for the whole TRE environment virtual network where workspaces networks will be created (can include the core network as well). E.g. `10.0.0.0/12`|
| `TERRAFORM_STATE_CONTAINER_NAME` | Optional. The name of the blob container to hold the Terraform state. Default value is `tfstate`. |
| `CORE_APP_SERVICE_PLAN_SKU` | Optional. The SKU used for AppService plan for core infrastructure. Default value is `P1v2`. |
| `WORKSPACE_APP_SERVICE_PLAN_SKU` | Optional. The SKU used for AppService plan used in E2E tests. Default value is `P1v2`. |
| `RESOURCE_PROCESSOR_NUMBER_PROCESSES_PER_INSTANCE` | Optional. The number of processes to instantiate when the Resource Processor starts. Equates to the number of parallel deployment operations possible in your TRE. Defaults to `5`. |

### Configure Authentication Secrets

In a previous [Setup Auth configuration](./setup-auth-entities.md) step a new `/devops/auth.env` env file was created. Go to this file and add those env vars to your github environment:

  | Variable | Description |
  | -------- | ----------- |
  | `AAD_TENANT_ID` | Tenant id against which auth is performed. |
  | `APPLICATION_ADMIN_CLIENT_ID`| This client will administer AAD Applications for TRE |
  | `APPLICATION_ADMIN_CLIENT_SECRET`| This client will administer AAD Applications for TRE |
  | `TEST_ACCOUNT_CLIENT_ID`| This will be created by default, but can be disabled by editing `/devops/scripts/create_aad_assets.sh`. This is the user that will run the tests for you |
  | `TEST_ACCOUNT_CLIENT_SECRET` | This will be created by default, but can be disabled by editing `/devops/scripts/create_aad_assets.sh`. This is the user that will run the tests for you |
  | `API_CLIENT_ID` | API application (client) ID. |
  | `API_CLIENT_SECRET` | API application client secret. |
  | `SWAGGER_UI_CLIENT_ID` | Swagger (OpenAPI) UI application (client) ID. |
  | `TEST_WORKSPACE_APP_ID`| Each workspace is secured behind it's own AD Application. Use the value of `WORKSPACE_API_CLIENT_ID` created in the `/devops/auth.env` env file |
  | `TEST_WORKSPACE_APP_SECRET`| Each workspace is secured behind it's own AD Application. This is the secret for that application. Use the value of `WORKSPACE_API_CLIENT_SECRET` created in the `/devops/auth.env` env file|

### Create a Teams Webhook for deployment notifications

The `deploy_tre.yml` workflow sends a notification to a Microsoft Teams channel when it finishes running.

!!! note
    If you don't want to notify a channel, you can also remove the **Notify dedicated teams channel** steps in the workflow

1. Follow the [Microsoft Docs](https://docs.microsoft.com/en-us/microsoftteams/platform/webhooks-and-connectors/how-to/add-incoming-webhook) to create a webhook for your channel

1. Configure the MS_TEAMS_WEBHOOK_URI repository secret

  | <div style="width: 230px">Secret name</div> | Description |
  | ----------- | ----------- |
  | `MS_TEAMS_WEBHOOK_URI` | URI for the Teams channel webhook |


!!! info
    See [Environment variables](../environment-variables.md) for full details of the deployment related variables.

### Setup Github env in workflow

In your repository you will find that the pipelines under the folder `.github/workflows` on top of each workflow there is the workflow inputs part where the used Github environment name is set, make sure to update it with yours, for example:

![Setup env in pipeline](../../assets/using-tre/pipelines_set_env.png)

### Deploy the TRE using the workflow

With all the repository secrets set, you can trigger a workflow run by pushing to develop/main of your repo, or by dispatching the workflow manually.

## Next steps

* [Deploying Azure TRE in Pipelines](cicd-deplyment.md)
