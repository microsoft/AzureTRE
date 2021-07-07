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
- An Azure Active Directory Service Principal  
  (Instructions later in this quickstart)

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

To create a new service principal with the Contributor role, run the following command. Make note of the `clientId` and `clientSecret` values returned and add them to the respective variables in the `.env` file.

```cmd
az ad sp create-for-rbac --name "sp-aztre-deployment-processor" --role Contributor --scopes /subscriptions/<subscription ID> --sdk-auth
```

<!-- markdownlint-disable-next-line MD013 -->
> *) The creation of the service principal with "Contributor" role is explained in [CD setup guide](./cd-setup.md#create-service-principals).  The `tre-deploy` target in the [Makefile](../Makefile) runs [a script](../devops/scripts/set_contributor_sp_secrets.sh) that inserts the client ID and secret into a Key Vault created in the same very step. If the script fails, the system will be up and running, but the deployment processor function will not be able to deploy workspace resources.

Your `.env` file should now look something similar to this:

```plaintext
# Management infrastructure
ARM_SUBSCRIPTION_ID=8cf4..65a0
LOCATION=norwayeast
MGMT_RESOURCE_GROUP_NAME=aztremgmt
MGMT_STORAGE_ACCOUNT_NAME=aztremgmt
TERRAFORM_STATE_CONTAINER_NAME=tfstate
IMAGE_TAG=dev
ACR_NAME=aztre

# Service Principal used by the Composition Service to provision workspaces
CONTRIBUTOR_SP_CLIENT_ID=8cf4..65ae
CONTRIBUTOR_SP_CLIENT_SECRET=secret
```

#### Optional environment variables

The below environment variables have to be set when deploying from a CD pipeline or testing Workspace bundles (Porter bundles) locally.

| Environment variable name | Description |
| ------------------------- | ----------- |
| `ARM_SUBSCRIPTION_ID` | *Optional for manual deployment.* The Azure subscription ID for all resources. |
| `ARM_TENANT_ID` | *Optional for manual deployment.* The Azure tenant ID. |
| `ARM_CLIENT_ID` | *Optional for manual deployment.* The client (app) ID of a service principal with "Owner" role to the subscription. Used by the GitHub Actions workflows to deploy TRE. |
| `ARM_CLIENT_SECRET` | *Optional for manual deployment.* The client secret (app password) of a service principal with "Owner" role to the subscription. Used by the GitHub Actions workflows to deploy TRE. |
| `PORTER_DRIVER` | *Optional for manual deployment.* Valid values are `docker` or `azure`. If deploying manually use `docker` if using Azure Container Instances and the [Azure CNAB Driver](https://github.com/deislabs/cnab-azure-driver) use `azure` |

### Bootstrap the back-end state

As a principle, we want all the Azure TRE resources defined in Terraform, including the storage account used by Terraform to hold its back-end state.

A bootstrap script is used to creates the initial storage account and resource group using the Azure CLI. Then Terraform is initialized using this storage account as a back-end, and the storage account imported into the state.

- From bash run `make bootstrap`

This script should never need running a second time even if the other management resources are modified.

### Management Resource Deployment

The deployment of the rest of the shared management resources is done via Terraform, and the various `.tf` files in the root of this repo.

- From bash run `make mgmt-deploy`

This Terraform creates & configures the following:

- Resource Group (also in bootstrap).
- Storage Account for holding Terraform state (also in bootstrap).
- Azure Container Registry.

### Build and push Docker images

Build and push the docker images required by the Azure TRE and publish them to the container registry created in the previous step. Run the following commands in bash:

```bash
make build-api-image
make build-cnab-image
make build-processor-function-image
make push-api-image
make-push-processor-function-image
make push-cnab-image
```

## Deploy an Azure TRE instance

### Configuring variables

Copy [/templates/core/.env.sample](../templates/core/.env.sample) to `/templates/core/.env` and set values for all variables described in the table below:

```cmd
cp templates/core/.env.sample templates/core/.env
```

| Environment variable name | Description |
| ------------------------- | ----------- |
| `TRE_ID` | A globally unique identifier. `TRE_ID` can be found in the resource names of the Azure TRE instance; for example, a `TRE_ID` of `mytre-dev-3142` will result in a resource group name for Azure TRE instance of `rg-mytre-dev-3142`. This must be less than 12 characters. Allowed characters: Alphanumeric, underscores, and hyphens. |
| `ADDRESS_SPACE` | The address space for the Azure TRE core virtual network. |
| `MANAGEMENT_API_IMAGE_TAG` | The tag of the management API image.  Set to the same value as `IMAGE_TAG` unless need to deploy different versions of each image. |
| `PROCESSOR_FUNCTION_API_IMAGE_TAG` | The tag of the processor function image that will be deployed. Set to the same value as `IMAGE_TAG` unless need to deploy different versions of each image. |

### Deploy

The deployment of the Azure TRE is done via Terraform. Run:

```cmd
make tre-deploy
```

Once the deployment is complete, you will see a few output parameters which are the result of your deployment.

```plaintext
app_gateway_name = "agw-<TRE_ID>"
azure_tre_fqdn = "<TRE_ID>.norwayeast.cloudapp.azure.com"
core_resource_group_name = "rg-<TRE_ID>"
keyvault_name = "kv-<TRE_ID>"
log_analytics_name = "log-<TRE_ID>"
static_web_storage = "stwebaz<TRE_ID>"
```

The Azure TRE is initially deployed with an invalid self-signed SSL certificate. This certificate is stored in the deployed Key Vault. To update the certificate in Key Vault needs to be replaced with one valid for the configured domain name. To use a certificate from [Let's Encrypt][letsencrypt], simply run the command:

```cmd
make letsencrypt
```

Note that there are rate limits with Let's Encrypt, so this should not be run when not needed.

### Access the Azure TRE deployment

To get the Azure TRE URL, view `azure_tre_fqdn` in the output of the previous `make tre-deploy` command, or run the following command to see it again:

```cmd
cd templates/core/terraform
terraform output azure_tre_fqdn
```

Open the following URL in a browser and you should see the Open API docs for the Azure TRE management API.

```plaintext
https://<azure_tre_fqdn>/docs
```

You can also create a request to the `api/health` endpoint to verify that the management API is deployed and responds. You should see a *pong* response as a result of below request.

```cmd
curl https://<azure_tre_fqdn>/api/health
```

## Deleting the Azure TRE deployment

To remove the Azure TRE and its resources from your Azure subscription run:

```cmd
make tre-destroy
```

[letsencrypt]: https://letsencrypt.org/ "A nonprofit Certificate Authority providing TLS certificates to 260 million websites."
