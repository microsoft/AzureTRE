# Setting up GitHub Actions workflows

These are onetime configuration steps required to set up the GitHub Actions workflows (pipelines). After the steps the [TRE deployment workflow](../.github/workflows/deploy_tre.yml) is ready to run.

## Create service principals

Two service principals need to be created: One to authorize the workflow itself and another for the deployment processor to provision resources for the TRE workspaces and workspace services.

1. Login with Azure CLI and set the subscription used by TRE:

    ```cmd
    az account set --subscription <subscription ID>
    ```

1. Create the workflow service principal with "owner" role:

    ```cmd
    az ad sp create-for-rbac --name "MyTREAppDeployment" --role Owner --scopes /subscriptions/<subscription ID> --sdk-auth
    ```

1. Save the JSON output in a [GitHub secret](https://docs.github.com/en/actions/reference/encrypted-secrets) called `AZURE_CREDENTIALS`.

1. Create the service principal, used by the deployment processor, that has contributor privileges:

    ```cmd
    az ad sp create-for-rbac --name "sp-msfttre-deployment-processor" --role Contributor --scopes /subscriptions/<subscription ID> --sdk-auth
    ```

1. Save the JSON output in a GitHub secret called `AZURE_CONTRIBUTOR_SP`.

## Set other sercrets

You will also need to create the following secrets:

- `TRE_ID`
- `ACR_NAME`
- `MGMT_RESOURCE_GROUP`
- `STATE_STORAGE_ACCOUNT_NAME`
- `TF_STATE_CONTAINER`
- `LOCATION`
- `ADDRESS_SPACE`

For descriptions of what each of these variables are, and example values, please review [Developer quickstart guide](./developer-quickstart.md).
