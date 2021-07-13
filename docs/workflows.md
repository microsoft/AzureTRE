# GitHub Actions workflows (CI/CD)

## Setup instructions

These are onetime configuration steps required to set up the GitHub Actions workflows (pipelines). After the steps the [TRE deployment workflow](../.github/workflows/deploy_tre.yml) is ready to run.

### Create service principals

Two service principals need to be created: One to authorize the workflow itself and another for the deployment processor to provision resources for the TRE workspaces and workspace services.

1. Login with Azure CLI and set the subscription used by TRE:

    ```cmd
    az account set --subscription <subscription ID>
    ```

1. Create the workflow service principal with "Owner" role:

    ```cmd
    az ad sp create-for-rbac --name "MyTREAppDeployment" --role Owner --scopes /subscriptions/<subscription ID> --sdk-auth
    ```

1. Save the JSON output in a [GitHub secret](https://docs.github.com/en/actions/reference/encrypted-secrets) called `AZURE_CREDENTIALS`.

1. Create the service principal, used by the deployment processor, that has contributor privileges:

    ```cmd
    az ad sp create-for-rbac --name "sp-msfttre-deployment-processor" --role Contributor --scopes /subscriptions/<subscription ID> --sdk-auth
    ```

1. Save the JSON output in a GitHub secret called `AZURE_CONTRIBUTOR_SP`.

### Set other sercrets

You will also need to create the following [repository secrets](https://docs.github.com/en/actions/reference/encrypted-secrets):

| Secret name | Description |
| ----------- | ----------- |
| `AZURE_CREDENTIALS` | Explained [above](#create-service-principals). |
| `AZURE_CONTRIBUTOR_SP` | Explained [above](#create-service-principals). |
| `TF_STATE_CONTAINER` | The name of the blob container to hold the Terraform state. Default value is `tfstate`. |
| `MGMT_RESOURCE_GROUP` | The name of the shared resource group for all Azure TRE core resources. |
| `STATE_STORAGE_ACCOUNT_NAME` | The name of the storage account to hold the Terraform state and other deployment artifacts. |
| `LOCATION` | The Azure location (region) for all resources. |
| `ACR_NAME` | A globally unique name for the Azure Container Registry (ACR) that will be created to store deployment images. |
| `PORTER_OUTPUT_CONTAINER_NAME` | The name of the storage container where to store the workspace/workspace service deployment output. Workspaces and workspace templates are implemented using [Porter](https://porter.sh) bundles - hence the name of the secret. The storage account used is the same as defined by `STATE_STORAGE_ACCOUNT_NAME`. |
| `TRE_ID` | A globally unique identifier. `TRE_ID` can be found in the resource names of the Azure TRE instance; for example, a `TRE_ID` of `tre-dev-42` will result in a resource group name for Azure TRE instance of `rg-tre-dev-42`. This must be less than 12 characters. Allowed characters: Alphanumeric, underscores, and hyphens. |
| `ADDRESS_SPACE` |  The address space for the Azure TRE core virtual network. |
| `SWAGGER_UI_CLIENT_ID` | The application (client) ID of the [TRE Swagger UI](./auth.md#tre-swagger-ui) service principal. |
| `AAD_TENANT_ID` | The tenant ID of the Azure AD. |
| `API_CLIENT_ID` | The application (client) ID of the [TRE API](./auth.md#tre-api) service principal. |
| `API_CLIENT_SECRET` | The application password (client secret) of the [TRE API](./auth.md#tre-api) service principal. |
