# GitHub Actions workflows (CI/CD)

## Setup instructions

These are onetime configuration steps required to set up the GitHub Actions workflows (pipelines). After the steps the [TRE deployment workflow](../.github/workflows/deploy_tre.yml) is ready to run.

1. Create service principals and set their [repository secrets](https://docs.github.com/en/actions/reference/encrypted-secrets) as explained in [Bootstrapping](./bootstrapping.md#create-service-principals)
1. Create app registrations for auth based on the [Authentication & authorization](./auth.md) guide
1. Set other repository secrets as explained in the table below

*Required repository secrets for the CI/CD.*
| Secret name | Description |
| ----------- | ----------- |
| `AZURE_CREDENTIALS` | Explained in [Bootstrapping - Create service principals](./bootstrapping.md#create-service-principals). |
| `AZURE_CONTRIBUTOR_SP` | Explained in [Bootstrapping - Create service principals](./bootstrapping.md#create-service-principals). |
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
