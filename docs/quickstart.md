# Azure TRE Deployment QuickStart

By following this quickstart, you will deploy a new Azure TRE instance for development and testing purposes.

The most straightforward way to get up and running is to deploy direct from the `microsoft/AzureTRE` repository.

Production deployments should take advantage of your chosen DevOps CD tooling.

> The quickstart assumes usage of Linux or WSL on Windows.

## Prerequisites

You will require the following prerequisites installed.

- Terraform >= v0.15.3
- Azure CLI >= 2.21.0
- Docker

> The above prerequisites will already be present if you are using GitHub Codespaces, or the provided Dev Container in VS Code.

You will also need:

- An Azure Subscription

## Clone the repository

Clone the repository to your local machine ( `git clone https://github.com/microsoft/AzureTRE.git` ), or you may choose to use our pre-configured dev container via GitHub Codespaces.

![Clone Options](../docs/assets/clone_options.png)

## Management Infrastructure

In the following steps we will create management infrastructure in your subscription. This includes resources, such as a storage account and container registry that will enable deployment the Azure TRE. Once the infrastructure is deployed we will build the container images required for deployment. The management infrastructure can serve multiple Azure TRE deployments.

### Log into your chosen Azure subscription

Login and select the Azure subscription you wish to deploy to:

```cmd
az login
az account list
az account set -s <subscription_name_or_id>
```

### Configuration

Before running any of the scripts, the configuration variables need to be set. This is done in an `.env` file, and this file is read and parsed by the scripts.

> Note: `.tfvars` file is not used, this is intentional. The `.env` file format is easier to parse, meaning we can use the values for bash scripts and other purposes.

Copy [/devops/.env.sample](../devops/.env.sample) to `/devops/.env`.

```cmd
cp devops/.env.sample devops/.env
```

 Then, open the `.env` file in a text editor and set the values for the required variables described in the table below:

| Environment variable name | Description |
| ------------------------- | ----------- |
| `LOCATION` | The Azure location (region) for all resources. |
| `MGMT_RESOURCE_GROUP_NAME` | The shared resource group for all management resources, including the storage account. |
| `MGMT_STORAGE_ACCOUNT_NAME` | The name of the storage account to hold the Terraform state and other deployment artifacts. |
| `TERRAFORM_STATE_CONTAINER_NAME` | The name of the blob container to hold the Terraform state *Default value is `tfstate`.* |
| `IMAGE_TAG` | The default tag for Docker images that will be pushed to the container registry and deployed with the Azure TRE. |
| `ACR_NAME` | A globally unique name for the Azure Container Registry (ACR) that will be created to store deployment images. |
| `CONTRIBUTOR_SP_CLIENT_ID` * | The client (app) ID of a service principal with "Contributor" role to the subscription. Used by the deployment processor function to deploy workspaces and workspace services. |
| `CONTRIBUTOR_SP_CLIENT_SECRET` * | The client secret (app password) of a service principal with "Contributor" role to the subscription. Used by the deployment processor function to deploy workspaces and workspace services. |

<!-- markdownlint-disable-next-line MD013 -->
> *) The creation of the service principal with "Contributor" role is explained in [CD setup guide](./cd-setup.md#create-service-principals). `tre-deploy` target in [Makefile](../Makefile) runs [a script](../devops/scripts/set_contributor_sp_secrets.sh) that inserts the client ID and secret into a Key Vault created in the same very step. If the script fails, the system will be up and running, but the deployment processor function will not be able to deploy workspace resources.

#### Optional environment variables

The below environment variables have to be set when deploying from a CD pipeline or similar setup.

| Environment variable name | Description |
| ------------------------- | ----------- |
| `ARM_TENANT_ID` | *Optional for manual deployment.* The Azure tenant ID. |
| `ARM_SUBSCRIPTION_ID` | *Optional for manual deployment.* The Azure subscription ID for all resources. |
| `ARM_CLIENT_ID` | *Optional for manual deployment.* The client (app) ID of a service principal with "Owner" role to the subscription. Used by the GitHub Actions workflows to deploy TRE. |
| `ARM_CLIENT_SECRET` | *Optional for manual deployment.* The client secret (app password) of a service principal with "Owner" role to the subscription. Used by the GitHub Actions workflows to deploy TRE. |

### Bootstrap of back-end state

As a principle we want all our resources defined in Terraform, including the storage account used by Terraform to hold back-end state. This results in a chicken and egg problem.

To solve this a bootstrap script is used which creates the initial storage account and resource group using the Azure CLI. Then Terraform is initialized using this storage account as a back-end, and the storage account imported into state

- From bash run `make bootstrap`

This script should never need running a second time even if the other management resources are modified.

### Management Resource Deployment

The deployment of the rest of the shared management resources is done via Terraform, and the various `.tf` files in the root of this repo.

- From bash run `make mgmt-deploy`

This Terraform creates & configures the following:

- Resource Group (also in bootstrap).
- Storage Account for holding Terraform state (also in bootstrap).
- Azure Container Registry.

### Build and push docker images

Build and push the docker images required by the Azure TRE and publish them to the container registry created in the previous step. Run the following commands in bash:

```bash
make build-api-image
make build-cnab-image
make push-api-image
make push-cnab-image
```

## Deploy an Azure TRE instance

### Configuring variables

Copy [/templates/core/.env.sample](../templates/core/.env.sample) to `/templates/core/.env` and set values for all variables described in the table below:

| Environment variable name | Description |
| ------------------------- | ----------- |
| `TRE_ID` | A globally unique identifier. `TRE_ID` can be found in the resource names of the Azure TRE instance; for example, a `TRE_ID` of `mytre-dev-3142` will result in a resource group name for Azure TRE instance of `rg-mytre-dev-3142`. This must be less than 12 characters. Allowed characters: Alphanumeric, underscores, and hyphens. |
| `ADDRESS_SPACE` | The address space for the Azure TRE core virtual network. |
| `MANAGEMENT_API_IMAGE_TAG` | The tag of the management API image. |

### Deploy

The deployment of the Azure TRE is done via Terraform. Run:

```cmd
make tre-deploy
```

The Azure TRE is initially deployed with an invalid self-signed SSL certificate. This certificate is stored in the deployed KeyVault. To update the certificate in KeyVault needs to be repaced with one valid for the configured domain name. To use a certificate from [Let's Encrypt][letsencrypt], simply run the command:

```cmd
make letsencrypt
```

Note that there are rate limits with Let's Encrypt, so this should not be run when not needed.

### Access the Azure TRE deployment

To get the Azure TRE URL, view `azure_tre_fqdn` in the output of the previous command, or run the following command:

```cmd
cd templates/core/terraform
terraform output azure_tre_fqdn
```

## Deleting the AzureTRE deployment

To remove the Azure TRE and its resources from your Azure subscription run:

- Run `make tre-destroy`

[letsencrypt]: https://letsencrypt.org/ "A nonprofit Certificate Authority providing TLS certificates to 260 million websites."
