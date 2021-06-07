# Azure TRE Deployment QuickStart

The Azure TRE uses Terraform infrastructure as code templates that pull down Docker container images to run the web applications.

The most straightforward way to get up and running is to deploy direct from the `microsoft/AzureTRE` repository. Production deployments should take advantage of your chosen DevOps CD tooling.

> The quickstart assumes usage of Linux or WSL on Windows.

## Prerequisites

You will require the following prerequisites installed. They will already be present if using GitHub Codespaces, or use our Dev Container in VS Code.

- Terraform >= v0.15.3. The following instructions use local terraform state, you may want to consider [storing you state remotely in Azure](https://docs.microsoft.com/en-us/azure/developer/terraform/store-state-in-azure-storage)
- Azure CLI >= 2.21.0
- Docker

You will also need:

- An Azure Subscription
- A GitHub user id and [personal access token](https://docs.github.com/en/github/authenticating-to-github/creating-a-personal-access-token) with scope `packages:read`. This token is used to pull the web app Docker images. This can be any GitHub account, and does not need to be part of the Microsoft GitHub organisation.

## Clone the repository

Clone the repository to your local machine ( `git clone https://github.com/microsoft/AzureTRE.git` ), or you may choose to use our pre-configured dev container via GitHub Codespaces.

![Clone Options](../docs/assets/clone_options.png)

## Management Infrastructure

In the following steps we will create management infrastructure in your subscription. This includes resources, such as a storage account and container registry that will enable deployment the Azure TRE. Once the infrastructure is deployed we will build the container images required for deployment.

### Log into your chosen Azure subscription

Login and select the azure subscription you wish to deploy to:

```cmd
az login
az account list
az account set -s <subscription_name_or_id>
```

### Configuration

Before running any of the scripts, the configuration variables need to be set. This is done in an `.env` file, and this file is read and parsed by scripts.

Note. `.tfvars` file is not used, this is intentional. The `.env` file format is easier to parse, meaning we can use the values for bash scripts and other purposes

Copy [/devops/terraform/.env.sample](../devops/terraform/.env.sample) to `/devops/terraform/.env` and set values for all variables:

- `TF_VAR_state_storage` - The name of the storage account to hold Terraform state.
- `TF_VAR_mgmt_res_group` - The shared resource group for all management resources, including the storage account.
- `TF_VAR_state_container` - Name of the blob container to hold Terraform state (default: `tfstate`).
- `TF_VAR_location` - Azure region to deploy all resources into.
- `TF_VAR_image_tag` - Default tag for docker images that will be pushed to the container registry and deployed with the Azure TRE.
- `TF_VAR_acr_name` - Globally unique name for the ACR that will be create to store deployment images.

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

Copy [/templates/core/terraform/.env.sample](../templates/core/terraform/.env.sample) to `/templates/core/terraform/.env` and set values for all variables:

- `TF_VAR_address_space` - Address space for the Azure TRE core virtual network
- `TF_VAR_tre_id` - Globally unique identifier, `tre_id` can be found in the resource names of the Azure TRE instance; for example, a `tre_id` of `mytre-dev-3142` will result in a resource group name for Azure TRE instance of `rg-mytre-dev-3142`. This must be less than 12 characters (Alphanumeric, underscore, and hyphen allowed).

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
