# Bootstrapping

This document covers the steps that have to be executed manually before Azure TRE can be deployed using CI/CD.

## Login to Azure

Log in to Azure using `az login` and select the Azure subscription you wish to deploy Azure TRE to:

```cmd
az login
az account list
az account set --subscription <subscription ID>
```

!!! caution
    When running locally the credentials of the logged-in user will be used to deploy the infrastructure. Hence, it is essential that the user has enough permissions to deploy all resources.

See [Sign in with Azure CLI](https://docs.microsoft.com/cli/azure/authenticate-azure-cli) for more details.

## Create service principals

A service principal needs to be created to authorize CI/CD workflows to provision resources for the TRE workspaces and workspace services.

1. Create a main service principal with "**Owner**" role:

    ```cmd
    az ad sp create-for-rbac --name "sp-aztre-core" --role Owner --scopes /subscriptions/<subscription_id> --sdk-auth
    ```

1. Save the JSON output locally - as you will need it later.
1. Create a [GitHub secret](https://docs.github.com/en/actions/reference/encrypted-secrets) called `AZURE_CREDENTIALS` with the JSON output.

## Create app registrations

Create app registrations for auth based on the [Authentication & authorization](auth.md) guide.

## Bootstrap target in Makefile

As a principle, we want all the Azure TRE resources defined in Terraform, including the storage account used by Terraform to hold its back-end state.

A bootstrap script is used to create the initial storage account and resource group using the Azure CLI. Then Terraform is initialized using this storage account as a back-end, and the storage account imported into the state.

You bootstrap the environment using `make bootstrap`, but as stated above this is already part of `make all`.

This script should never need running a second time even if the other management resources are modified.
