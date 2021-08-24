# Deploying Azure TRE manually

By following this guide you will deploy a new Azure TRE instance for development and testing purposes.

## Steps

### Bootstrap and create prerequisite resources

1. By now you should have a [developer environment](./dev-environment.md) set up
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
| `ARM_SUBSCRIPTION_ID` | *Optional for manual deployment. If not specified the `az cli` selected subscription will be used.* The Azure subscription ID for all resources. |
| `ARM_CLIENT_ID` | *Optional for manual deployment without logged-in credentials.* The client whose azure identity will be used to deploy the solution. |
| `ARM_CLIENT_SECRET` | *Optional for manual deployment without logged-in credentials.* The password of the client defined in `ARM_CLIENT_ID`. |
| `ARM_TENANT_ID` | *Optional for manual deployment. If not specified the `az cli` selected subscription will be used.* The AAD tenant of the client defined in `ARM_CLIENT_ID`. |
| `PORTER_OUTPUT_CONTAINER_NAME` | The name of the storage container where to store the workspace/workspace service deployment output. Workspaces and workspace templates are implemented using [Porter](https://porter.sh) bundles - hence the name of the variable. The storage account used is the one defined in `STATE_STORAGE_ACCOUNT_NAME`. |
| `DEBUG` | If set to "true" disables purge protection of keyvault. |


Copy [/templates/core/.env.sample](../templates/core/.env.sample) to `/templates/core/.env` and set values for all variables described in the table below:

```cmd
cp templates/core/.env.sample templates/core/.env
```

| Environment variable name | Description |
| ------------------------- | ----------- |
| `TRE_ID` | A globally unique identifier. `TRE_ID` can be found in the resource names of the Azure TRE instance; for example, a `TRE_ID` of `mytre-dev-3142` will result in a resource group name for Azure TRE instance of `rg-mytre-dev-3142`. This must be less than 12 characters. Allowed characters: Alphanumeric, underscores, and hyphens. |
| `ADDRESS_SPACE` | The address space for the Azure TRE core virtual network. `/22` or larger. |
| `MANAGEMENT_API_IMAGE_TAG` | The tag of the Management API image. Make it the same as `IMAGE_TAG` above.|
| `RESOURCE_PROCESSOR_VMSS_PORTER_IMAGE_TAG` | The tag of the resource processor image. Make it the same as `IMAGE_TAG` above.|
| `GITEA_IMAGE_TAG` | The tag of the Gitea image. Make it the same as `IMAGE_TAG` above.|
| `SWAGGER_UI_CLIENT_ID` | Generated when following auth guide. Client ID for swagger client to make requests. |
| `AAD_TENANT_ID` | Generated when following auth guide. Tenant id against which auth is performed. |
| `API_CLIENT_ID` | Generated when following auth guide. Client id of the "TRE API". |
| `API_CLIENT_SECRET` | Generated when following auth guide. Client secret of the "TRE API". |
| `DEPLOY_GITEA` | If set to `false` disables deployment of the Gitea shared service. |
| `DEPLOY_NEXUS` | If set to `false` disables deployment of the Nexus shared service. |

### Deploy

The deployment of the Azure TRE is done via Terraform. Run:

```cmd
make all
```

Once the deployment is complete, you will see a few output parameters which are the result of your deployment.

```plaintext
app_gateway_name = "agw-<TRE_ID>"
azure_tre_fqdn = "<TRE_ID>.<LOCATION>.cloudapp.azure.com"
core_resource_group_name = "rg-<TRE_ID>"
keyvault_name = "kv-<TRE_ID>"
log_analytics_name = "log-<TRE_ID>"
static_web_storage = "stwebaz<TRE_ID>"
```

The Azure TRE is initially deployed with an invalid self-signed SSL certificate. This certificate is stored in the deployed Key Vault and can/should be replaced with one valid for the configured domain name. To use a certificate from [Let's Encrypt][letsencrypt], simply run the command:

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
make build-resource-processor-vm-porter-image
make push-api-image
make push-resource-processor-vm-porter-image
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

## Publishing and registering the base workspace bundle

1. Run:

    ```cmd
    register-bundle DIR=./templates/workspaces/base
    ```

    Copy the resulting payload json.

1. Navigate to the Swagger UI at `https://<azure_tre_fqdn>/docs`

1. Log into the Swagger UI by clicking `Authorize`, then `Authorize` again. You will be redirected to the login page.

1. Once logged in. Click `Try it out` on the `POST` `/api/workspace-templates` operation:

    ![Post Workspace Template](./assets/post-template.png)

1. Paste the payload json generated earlier into the `Request body` field, then click `Execute`. Review the server response.

1. To verify regsitration of the template do `GET` operation on `/api/workspace-templates`. The name of the template should now be listed.

## Creating a base workspace

Now that we have published and registered a base workspace bundle we can use the deployed API to create a base workspace.

<!-- markdownlint-disable-next-line MD013 -->
> All routes are auth protected.Click the green **Authorize** button to receive a token for swagger client.  

As explained in the [auth guide](auth.md), every workspace has a corresponding app registration which can be created using the helper script [../scripts/workspace-app-reg.py](../scripts/workspace-app-reg.py). Multiple workspaces can share an app registration.

Running the script will report app id of the generated app which needs to be used in the POST body below.

Go to ``azure_tre_fqdn/docs`` and use POST /api/workspaces with the sample body to create a base workspace.

```json
{
  "displayName": "manual-from-swagger",
  "description": "workspace for team X",
  "workspaceType": "tre-workspace-base",
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
