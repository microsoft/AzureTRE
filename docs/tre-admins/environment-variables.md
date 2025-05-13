# Environment variables

!!! info
    The `.tfvars` file is intentionally not used. The `.env` file format is easier to parse, meaning we can use the values for bash scripts and other purposes.

## For shared management resources in `/config.yaml`

| <div style="width: 330px">Environment variable name</div> | Description |
| ------------------------- | ----------- |
| `LOCATION` | The Azure location (region) for all resources. |
| `MGMT_RESOURCE_GROUP_NAME` | The shared resource group for all management resources, including the storage account. |
| `MGMT_STORAGE_ACCOUNT_NAME` | The name of the storage account to hold the Terraform state and other deployment artifacts. |
| `TERRAFORM_STATE_CONTAINER_NAME` | The name of the blob container to hold the Terraform state *Default value is `tfstate`.* |
| `ACR_NAME` | A globally unique name for the Azure Container Registry (ACR) that will be created to store deployment images. |
| `EXTERNAL_KEY_STORE_ID` | The ID of the external Key Vault to store CMKs in. Should not be set if `ENCRYPTION_KV_NAME` is set and only required if `ENABLE_CMK_ENCRYPTION` is true. |
| `ENCRYPTION_KV_NAME` | The name of the Key Vault for encryption keys. Should not be set if `EXTERNAL_KEY_STORE_ID` is set and only required if `ENABLE_CMK_ENCRYPTION` is true. |
| `ARM_SUBSCRIPTION_ID` | *Optional for manual deployment. If not specified the `az cli` selected subscription will be used.* The Azure subscription ID for all resources. |
| `ARM_CLIENT_ID` | *Optional for manual deployment without logged-in credentials.* The client whose azure identity will be used to deploy the solution. |
| `ARM_CLIENT_SECRET` | *Optional for manual deployment without logged-in credentials.* The password of the client defined in `ARM_CLIENT_ID`. |
| `ARM_TENANT_ID` | *Optional for manual deployment. If not specified the `az cli` selected subscription will be used.* The Microsoft Entra ID tenant of the client defined in `ARM_CLIENT_ID`. |

## For Azure TRE instance in `/config.yaml`

| <div style="width: 330px">Environment variable name</div> | Description |
| ------------------------- | ----------- |
| `TRE_ID` | A globally unique identifier. `TRE_ID` can be found in the resource names of the Azure TRE instance; for example, a `TRE_ID` of `mytre-dev` will result in a resource group name for Azure TRE instance of `rg-mytre-dev`. This must be less than 12 characters. Allowed characters: lowercase alphanumerics|
| `TRE_URL`| This will be generated for you by populating your `TRE_ID`. This is used so that you can automatically register bundles |
| `CORE_ADDRESS_SPACE` | The address space for the Azure TRE core virtual network. `/22` or larger. |
| `TRE_ADDRESS_SPACE` | The address space for the whole TRE environment virtual network where workspaces networks will be created (can include the core network as well). E.g. `10.0.0.0/12`|
| `ENABLE_SWAGGER` | Determines whether the Swagger interface for the API will be available. |
| `SWAGGER_UI_CLIENT_ID` | Generated when following [pre-deployment steps](./setup-instructions/setup-auth-entities.md) guide. Client ID for swagger client to make requests. |
| `AAD_TENANT_ID` | Generated when following [pre-deployment steps](./setup-instructions/setup-auth-entities.md) guide. Tenant id against which auth is performed. |
| `API_CLIENT_ID` | Generated when following [pre-deployment steps](./setup-instructions/setup-auth-entities.md) guide. Client id of the "TRE API". |
| `API_CLIENT_SECRET` | Generated when following [pre-deployment steps](./setup-instructions/setup-auth-entities.md) guide. Client secret of the "TRE API". |
| `STATEFUL_RESOURCES_LOCKED` | If set to `false` locks on stateful resources won't be created. A recommended setting for developers. |
| `KV_PURGE_PROTECTION_ENABLED` | If set to `false` the core Key Vault's purge protection will be disabled so it can be reused upon deletion. A recommended setting for developers. |
| `ENABLE_AIRLOCK_MALWARE_SCANNING` | If False, Airlock requests will skip the malware scanning stage. If set to True, Defender for Storage will be enabled. |
| `ENABLE_LOCAL_DEBUGGING` | Set to `false` by default. Setting this to `true` will ensure that Azure resources are accessible from your local development machine. (e.g. ServiceBus and Cosmos) |
| `PUBLIC_DEPLOYMENT_IP_ADDRESS` | The public IP address of the machine that is deploying TRE. (Your desktop or the build agents). In certain locations a dynamic script to retrieve this from [https://ipecho.net/plain](https://ipecho.net/plain) does not work. If this is the case, then you can 'hardcode' your IP. |
| `RESOURCE_PROCESSOR_VMSS_SKU` | The SKU of the VMMS to use for the resource processing VM. |
| `CORE_APP_SERVICE_PLAN_SKU` | The SKU of AppService plans created for the core infrastructure. |
| `WORKSPACE_APP_SERVICE_PLAN_SKU` | Optional. The SKU used for AppService plan used in E2E tests unless otherwise specified. Default value is `P1v2`. |
| `RESOURCE_PROCESSOR_NUMBER_PROCESSES_PER_INSTANCE` | Optional. The number of processes to instantiate when the Resource Processor starts. Equates to the number of parallel deployment operations possible in your TRE. Defaults to `5`. |
| `FIREWALL_SKU` | Optional. The SKU of the Azure Firewall instance. Default value is `Standard`. Allowed values [`Basic`, `Standard`, `Premium`]. See [Azure Firewall SKU feature comparison](https://learn.microsoft.com/en-us/azure/firewall/choose-firewall-sku). |
| `APP_GATEWAY_SKU` | Optional. The SKU of the Application Gateway. Default value is `Standard_v2`. Allowed values [`Standard_v2`, `WAF_v2`] |
| `DEPLOY_BASTION` | Optional. If set to `true`, an Azure Bastion instance will be deployed. Default value is `true`. |
| `BASTION_SKU` | Optional. The SKU of the Azure Bastion instance. Default value is `Basic`. Allowed values [`Developer`, `Standard`, `Basic`, `Premium`]. See [Azure Bastion SKU feature comparison](https://learn.microsoft.com/en-us/azure/bastion/bastion-overview#sku). |
| `CUSTOM_DOMAIN` | Optional. Custom domain name to access the Azure TRE portal. See [Custom domain name](custom-domain.md). |
| `ENABLE_CMK_ENCRYPTION` | Optional. Default is `false`, if set to `true` customer-managed key encryption will be enabled for all supported resources. |
| `AUTO_WORKSPACE_APP_REGISTRATION`| Set to `false` by default. Setting this to `true` grants the `Application.ReadWrite.All` and `Directory.Read.All` permission to the *Application Admin* identity. This identity is used to manage other Microsoft Entra ID applications that it owns, e.g. Workspaces. If you do not set this, the identity will have `Application.ReadWrite.OwnedBy` permission. [Further information on Application Admin can be found here](./identities/application_admin.md). |
| `AUTO_WORKSPACE_GROUP_CREATION`| Set to `false` by default. Setting this to `true` grants the `Group.ReadWrite.All` permission to the *Application Admin* identity. This identity can then create security groups aligned to each applciation role. Microsoft Entra ID licencing implications need to be considered as Group assignment is a premium feature. [You can read mode about Group Assignment here](https://docs.microsoft.com/en-us/azure/architecture/multitenant-identity/app-roles#roles-using-azure-ad-app-roles). |
| `AUTO_GRANT_WORKSPACE_CONSENT`| Default of `false`.  Setting this to `true` will remove the need for users to manually grant consent when creating new workspaces. The identity will be granted `Application.ReadWrite.All` and `DelegatedPermissionGrant.ReadWrite.All` permissions. |
| `USER_MANAGEMENT_ENABLED` | If set to `true`, TRE Admins will be able to assign and de-assign users to workspaces via the UI (Requires Entra ID groups to be enabled on the workspace and the workspace template version to be 2.2.0 or greater). |
| `PRIVATE_AGENT_SUBNET_ID` | Optional. Vnet exception is enabled for the provided runner agent subnet id, enabling access to private resources like TRE key vault. |
| `UI_SITE_NAME` | Optional. Overrides the title text shown in top left corner of portal. Default value is: `Azure TRE`  |
| `UI_FOOTER_TEXT` | Optional. Overrides the footer text shown in the bottom left corner of the portal.  Default value is `Azure Trusted Research Environment` |

## For authentication in `/config.yaml`

  | Variable | Description |
  | -------- | ----------- |
  | `APPLICATION_ADMIN_CLIENT_ID`| This client will administer Microsoft Entra ID Applications for TRE |
  | `APPLICATION_ADMIN_CLIENT_SECRET`| This client will administer Microsoft Entra ID Applications for TRE |
  | `TEST_ACCOUNT_CLIENT_ID`| This will be created by default, but can be disabled by editing `/devops/scripts/create_aad_assets.sh`. This is the user that will run the tests for you |
  | `TEST_ACCOUNT_CLIENT_SECRET` | This will be created by default, but can be disabled by editing `/devops/scripts/create_aad_assets.sh`. This is the user that will run the tests for you |
  | `API_CLIENT_ID` | API application (client) ID. |
  | `API_CLIENT_SECRET` | API application client secret. |
  | `SWAGGER_UI_CLIENT_ID` | Swagger (OpenAPI) UI application (client) ID. |
  | `WORKSPACE_API_CLIENT_ID` | Each workspace is secured behind it's own AD Application|
  | `WORKSPACE_API_CLIENT_SECRET` | Each workspace is secured behind it's own AD Application. This is the secret for that application.|

## For CI/CD pipelines in github environment secrets

  | Variable | Description |
  | -------- | ----------- |
  | `AZURE_CREDENTIALS`| Credentials used to authorize CI/CD workflows to provision resources for the TRE workspaces and workspace services. This is basically your ARM client credentials in json format. Read more about how to create it and its format [here](./setup-instructions/workflows.md##create-a-service principal-for-provisioning-resources)|
  | `MS_TEAMS_WEBHOOK_URI` | URI for the Teams channel webhook |
