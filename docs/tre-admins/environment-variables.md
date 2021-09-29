# Environment variables

!!! info
    The `.tfvars` file is intentionally not used. The `.env` file format is easier to parse, meaning we can use the values for bash scripts and other purposes.

## For shared management resources in `/devops/.env`

| <div style="width: 330px">Environment variable name</div> | Description |
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
| `DEBUG` | If set to "true" disables purge protection of keyvault. |

## For Azure TRE instance in `/templates/core/.env`

| <div style="width: 330px">Environment variable name</div> | Description |
| ------------------------- | ----------- |
| `TRE_ID` | A globally unique identifier. `TRE_ID` can be found in the resource names of the Azure TRE instance; for example, a `TRE_ID` of `mytre-dev` will result in a resource group name for Azure TRE instance of `rg-mytre-dev`. This must be less than 12 characters. Allowed characters: Alphanumeric, underscores, and hyphens. |
| `CORE_ADDRESS_SPACE` | The address space for the Azure TRE core virtual network. `/22` or larger. |
| `TRE_ADDRESS_SPACE` | The address space for the whole TRE environment virtual network where workspaces networks will be created (can include the core network as well). E.g. `10.0.0.0/12`|
| `API_IMAGE_TAG` | The tag of the API image. Make it the same as `IMAGE_TAG` above.|
| `RESOURCE_PROCESSOR_VMSS_PORTER_IMAGE_TAG` | The tag of the resource processor image. Make it the same as `IMAGE_TAG` above.|
| `GITEA_IMAGE_TAG` | The tag of the Gitea image. Make it the same as `IMAGE_TAG` above.|
| `SWAGGER_UI_CLIENT_ID` | Generated when following auth guide. Client ID for swagger client to make requests. |
| `AAD_TENANT_ID` | Generated when following auth guide. Tenant id against which auth is performed. |
| `API_CLIENT_ID` | Generated when following auth guide. Client id of the "TRE API". |
| `API_CLIENT_SECRET` | Generated when following auth guide. Client secret of the "TRE API". |
| `DEPLOY_GITEA` | If set to `false` disables deployment of the Gitea shared service. |
| `DEPLOY_NEXUS` | If set to `false` disables deployment of the Nexus shared service. |
