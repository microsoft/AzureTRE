# Deploying Azure TRE manually

By following this guide you will deploy a new Azure TRE instance for development and testing purposes.

The most straightforward way to get up and running is to deploy direct from the [`microsoft/AzureTRE`](https://github.com/microsoft/AzureTRE) repository.

## Steps

### Bootstrap and create prerequisite resources

1. By now you should have a [developer environment](./dev-environment.md) set up
1. Create service principals as explained in [Bootstrapping](./bootstrapping.md) document
1. Create app registrations for auth; follow the [Authentication & authorization](./auth.md) guide

### Configure variables

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
| `ARM_SUBSCRIPTION_ID` | *Optional for manual deployment.* The Azure subscription ID for all resources. |
| `RESOURCE_PROCESSOR_CLIENT_ID` | The client (app) ID of a service principal with "Owner" role to the subscription as created above. Used by Resource Processor Function to deploy workspaces and workspace services. |
| `RESOURCE_PROCESSOR_CLIENT_SECRET` | The client secret (app password) of a service principal with "Onwer" role to the subscription as created above. Used by the depl09oyment processor function to deploy workspaces and workspace services. |
| `PORTER_DRIVER` | *Optional for manual deployment.* Valid values are `docker` or `azure`. If deploying manually use `docker` if using Azure Container Instances and the [Azure CNAB Driver](https://github.com/deislabs/cnab-azure-driver) use `azure` |
| `SWAGGER_UI_CLIENT_ID` | Generated when following auth guide. Client ID for swagger client to make requests. |
| `AAD_TENANT_ID` | Generated when following auth guide. Tenant id against which auth is performed. |
| `API_CLIENT_ID` | Generated when following auth guide. Client id of the "TRE API". |
| `API_CLIENT_SECRET` | Generated when following auth guide. Client secret of the "TRE API". |
| `DEBUG` | If set to "true" disables purge protection of keyvault. |

Your `.env` file should now look something similar to this:

```plaintext
# Management infrastructure
ARM_SUBSCRIPTION_ID=8cf4..65a0
LOCATION=norwayeast
MGMT_RESOURCE_GROUP_NAME=aztremgmt
MGMT_STORAGE_ACCOUNT_NAME=aztremgmt
TERRAFORM_STATE_CONTAINER_NAME=tfstate
IMAGE_TAG=v1
ACR_NAME=aztre

# Service Principal used by the Composition Service to provision workspaces
RESOURCE_PROCESSOR_CLIENT_ID=8cf4..65ae
RESOURCE_PROCESSOR_CLIENT_SECRET=secret

SWAGGER_UI_CLIENT_ID=bbfbfd5b...dd00
AAD_TENANT_ID=6ece...8aed
API_CLIENT_ID=f91b..6332
API_CLIENT_SECRET=secret

# Configure Porter to use docker or Azure CNAB driver
PORTER_DRIVER=docker
PORTER_OUTPUT_CONTAINER_NAME=porterout

# Debug mode
DEBUG="false"
```

Copy [/templates/core/.env.sample](../templates/core/.env.sample) to `/templates/core/.env` and set values for all variables described in the table below:

```cmd
cp templates/core/.env.sample templates/core/.env
```

| Environment variable name | Description |
| ------------------------- | ----------- |
| `TRE_ID` | A globally unique identifier. `TRE_ID` can be found in the resource names of the Azure TRE instance; for example, a `TRE_ID` of `mytre-dev-3142` will result in a resource group name for Azure TRE instance of `rg-mytre-dev-3142`. This must be less than 12 characters. Allowed characters: Alphanumeric, underscores, and hyphens. |
| `ADDRESS_SPACE` | The address space for the Azure TRE core virtual network. |
| `MANAGEMENT_API_IMAGE_TAG` | The tag of the Management API image. Make it the same as `IMAGE_TAG` above.|

### Deploy

The deployment of the Azure TRE is done via Terraform. Run:

```cmd
make all
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

Deploy the processor function:

```cmd
make deploy-processor-function
```

The Azure TRE is initially deployed with an invalid self-signed SSL certificate. This certificate is stored in the deployed Key Vault. To update the certificate in Key Vault needs to be replaced with one valid for the configured domain name. To use a certificate from [Let's Encrypt][letsencrypt], simply run the command:

```cmd
make letsencrypt
```

Note that there are rate limits with Let's Encrypt, so this should not be run when not needed.

## Details of deployment and infrastructure

The following section is for informational purpose and the steps don't need to be executed as they are part of make all above.

### Management Infrastructure

We will create management infrastructure in your subscription. This includes resources, such as a storage account and container registry that will enable deployment the Azure TRE. Once the infrastructure is deployed we will build the container images required for deployment. The management infrastructure can serve multiple Azure TRE deployments.

### Bootstrap the back-end state

As a principle, we want all the Azure TRE resources defined in Terraform, including the storage account used by Terraform to hold its back-end state.

A bootstrap script is used to creates the initial storage account and resource group using the Azure CLI. Then Terraform is initialized using this storage account as a back-end, and the storage account imported into the state.

You can do this step using the following command but as stated above this is already part of ``make all``.

- `make bootstrap`

This script should never need running a second time even if the other management resources are modified.

### Management Resource Deployment

The deployment of the rest of the shared management resources is done via Terraform, and the various `.tf` files in the root of this repo.

- `make mgmt-deploy`

This Terraform creates & configures the following:

- Resource Group (also in bootstrap).
- Storage Account for holding Terraform state (also in bootstrap).
- Azure Container Registry.

### Build and push Docker images

Build and push the docker images required by the Azure TRE and publish them to the container registry created in the previous step.

```bash
make build-api-image
make build-cnab-image
make push-api-image
make push-cnab-image
```

## Access the Azure TRE deployment

To get the Azure TRE URL, view `azure_tre_fqdn` in the output of the previous `make all` command, or run the following command to see it again:

```cmd
cd templates/core/terraform
terraform output azure_tre_fqdn
```

Open the following URL in a browser and you should see the Open API docs of Azure TRE Management API.

```plaintext
https://<azure_tre_fqdn>/docs
```

You can also create a request to the `api/health` endpoint to verify that Management API is deployed and responds. You should see a *pong* response as a result of below request.

```cmd
curl https://<azure_tre_fqdn>/api/health
```

## Creating vanilla workspace bundle and publishing them

Copy [workspaces/vanilla/.env.sample](../workspaces/vanilla/.env.sample) to `workspaces/vanilla/.env`.

```cmd
cp workspaces/vanilla/.env.sample workspaces/vanilla/.env
```

Edit the file and update the parameters

| Environment variable name | Description |
| ------------------------- | ----------- |
| `TRE_ID` | Same as used above for creating the TRE |
| `WORKSPACE_ID` | Random 4 characters ???|
| `ADDRESS_SPACE` | The address space for the Azure TRE core virtual network. |
| `AZURE_LOCATION` | Same as LOCATION above  |
| `ARM_CLIENT_ID` | Same as RESOURCE_PROCESSOR_CLIENT_ID |
| `ARM_CLIENT_SECRET` | Same as RESOURCE_PROCESSOR_CLIENT_SECRET |
| `ARM_TENANT_ID` | Tenant id where TRE is deployed |

Now you can run

```cmd
make porter-build DIR=./workspaces/vanilla
```

followed by

```cmd
make porter-publish DIR=./workspaces/vanilla
```

## Creating a vanilla workspace

Now that we have created a vanilla workspace bundle we can use the deployed API to create a vanilla workspace.

<!-- markdownlint-disable-next-line MD013 -->
> All routes are auth protected.Click the green **Authorize** button to receive a token for swagger client.  

As explained in the [auth guide](auth.md), every workspace has a corresponding app registration which can be created using the helper script [../scripts/workspace-app-reg.py](../scripts/workspace-app-reg.py). Multiple workspaces can share an app registration.

Running the script will report app id of the generated app which needs to be used in the POST body below.

Go to ``azure_tre_fqdn/docs`` and use POST /api/workspaces with the sample body to create a vanilla workspace.

```json
{
  "displayName": "manual-from-swagger",
  "description": "workspace for team X",
  "workspaceType": "tre-workspace-vanilla",
  "parameters": {},
  "authConfig": {
    "provider": "AAD",
    "data": {
      "app_id": "app id created above"
    }
  }
}
```

The API will report the ``workspace_id`` of the created workspce, which can be used to query deployment status by using ``/api/workspaces/<workspace_id>``

You can also follow the progess in Azure portal as various resources come up.

<!-- markdownlint-disable-next-line MD013 -->
> To query the status using the API your user needs to have TREResearcher or TREOwner role assigned to the app.

## Deleting the Azure TRE deployment

To remove the Azure TRE and its resources from your Azure subscription run:

```cmd
make tre-destroy
```

[letsencrypt]: https://letsencrypt.org/ "A nonprofit Certificate Authority providing TLS certificates to 260 million websites."
