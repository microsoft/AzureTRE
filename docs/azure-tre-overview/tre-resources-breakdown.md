# Azure TRE Resource Breakdown

## Azure TRE

Once an Azure TRE has been provisioned in an Azure Subscription, you will have a Resource Group named `rg-{TRE_ID}`.  An example TRE deployment is shown and described here.

[![Azure TRE Deployment Example](../assets/tre-example.png)](../assets/tre-resources-example.png)

| Name | Azure Service | Description | Additional links
|---|---|---|---|
| api-{TRE_ID} | App Service | Python api responsible for all operations on Workspaces and managing Workspace Templates | https://microsoft.github.io/AzureTRE/tre-developers/api/
| gitea-{TRE_ID} | App Service | Source Mirror - allows mirroring git repositories | https://microsoft.github.io/AzureTRE/azure-tre-overview/shared-services/gitea/
| nexus-{TRE_ID} | App Service | Package Mirror - allows mirroring packages | https://microsoft.github.io/AzureTRE/azure-tre-overview/shared-services/nexus/
| plan-{TRE_ID} | App Service Plan | Compute resources in which the TRE app services run | https://docs.microsoft.com/en-us/azure/app-service/overview-hosting-plans
| agw-{TRE_ID} | Azure Application Gateway | Provides single public IP address with SSL for accessing core TRE resources | https://microsoft.github.io/AzureTRE/azure-tre-overview/architecture/
| appi-{TRE_ID} | Application Insights | Telemetry for all API invocations | https://docs.microsoft.com/en-us/azure/azure-monitor/app/app-insights-overview
| cosmos-{TRE_ID} | Azure Cosmos DB Account | NoSQL state store of TRE resources, templates and operations | https://docs.microsoft.com/en-us/azure/cosmos-db/introduction
| mysql-{TRE_ID} | Azure Database for MySQL server | SQL state store for Gitea | https://docs.gitea.io/en-us/database-prep/
| ampls-{TRE_ID} | Azure Monitor Private Link Scope | Provides secure link between PaaS resources and the TRE vnet using private endpoints | https://docs.microsoft.com/en-us/azure/azure-monitor/logs/private-link-security
| bas-{TRE_ID} | Azure Bastion | Provides secure access for RDP/SSH to TRE VM (jumpbox) | https://docs.microsoft.com/en-us/azure/bastion/bastion-overview
| vm-dsk-{TRE_ID} | Disk | Managed storage disk for TRE VM (jumpbox) | https://docs.microsoft.com/en-us/azure/virtual-machines/managed-disks-overview
| fw-dsk-{TRE_ID} | Azure Firewall | Restricts external outbound traffic from all TRE resources | https://microsoft.github.io/AzureTRE/azure-tre-overview/networking/
| kv-{TRE_ID} | Azure Key Vault | Management of TRE secrets & certificates | https://docs.microsoft.com/en-us/azure/key-vault/general/overview
| log-{TRE_ID} | Log Analytics Workspace | Azure Monitor Logs store for all TRE resources | https://docs.microsoft.com/en-us/azure/azure-monitor/logs/data-platform-logs#log-analytics-workspaces
| id-agw-{TRE_ID} | Managed Identity | User-managed identity for TRE Application Gateway | https://docs.microsoft.com/en-us/azure/active-directory/managed-identities-azure-resources/overview
| id-api-{TRE_ID} | Managed Identity | User-managed identity for TRE API App Service | https://docs.microsoft.com/en-us/azure/active-directory/managed-identities-azure-resources/overview
| id-gitea-{TRE_ID} | Managed Identity | User-managed identity for TRE Gitea App Service | https://docs.microsoft.com/en-us/azure/active-directory/managed-identities-azure-resources/overview
| id-vmss-{TRE_ID} | Managed Identity | User-managed identity for TRE Resource Processer (VMSS) | https://docs.microsoft.com/en-us/azure/active-directory/managed-identities-azure-resources/overview
| sb-{TRE_ID} | Service Bus Namespace | Messaging for TRE API | https://docs.microsoft.com/en-us/azure/active-directory/managed-identities-azure-resources/overview
| stappinsights{TRE_ID} | Storage Account | Storage for TRE Application Insights telemetry logs | https://docs.microsoft.com/en-us/azure/storage/blobs/storage-blobs-overview
| stg{TRE_ID} | Storage Account | Files shares for TRE services such as Porter, Gitea, Nexus | https://docs.microsoft.com/en-us/azure/active-directory/managed-identities-azure-resources/overview | https://docs.microsoft.com/en-us/azure/storage/files/storage-files-introduction
| stweb{TRE_ID} | Storage Account | Storage for Let's Encrypt | https://microsoft.github.io/AzureTRE/tre-admins/setup-instructions/deploying-azure-tre/
| vm-{TRE_ID} | Virtual Machine | Azure TRE VM (jumpbox) | https://microsoft.github.io/AzureTRE/tre-admins/setup-instructions/configuring-shared-services/
| vm-{TRE_ID} | Virtual Machine Scale Set | Azure TRE Resource Processor | https://microsoft.github.io/AzureTRE/tre-developers/resource-processor/
| vnet-{TRE_ID} | Virtual Network | Azure TRE VNET central hub | https://microsoft.github.io/AzureTRE/azure-tre-overview/networking/
| rt-{TRE_ID} | Route Table | Azure TRE route  table | https://docs.microsoft.com/en-us/azure/virtual-network/manage-route-table

!!! note
    Network resources such as Network Interfaces, Network Security Groups, Private Endpoints, Private DNS zones and Public IP addresses are not listed above.

## Azure TRE Workspace

A TRE Workspace will be provisioned in a separate Resource Group along with its own resources.  An example TRE Workspace is shown and described here.

[![Azure TRE Workspace Example](../assets/tre-workspace-example.png)](../assets/tre-workspace-example.png)

| Name | Azure Service | Description | Additional links
|---|---|---|---|
| guacamole-{TRE_ID}-ws-XXXX-svc-XXXX	| App Service | RDP for accessing workspace VMs | https://microsoft.github.io/AzureTRE/tre-templates/workspace-services/guacamole/
| kv-{TRE_ID}-ws-XXXX | Azure	Key Vault | Management of TRE workspace secrets & certificates | https://docs.microsoft.com/en-us/azure/key-vault/general/overview
| osdisk-windowsvm8f45 | Disk | Azure VM storage disk | https://docs.microsoft.com/en-us/azure/virtual-machines/managed-disks-overview
| plan-09d0ba4f-f79f-4047-aa2c-03fc9df7b318 | App Service plan | Compute resources in which the workspace app services (Gitea) run | https://docs.microsoft.com/en-us/azure/app-service/overview-hosting-plans
| stgwsb318	| Storage account | Workspace Storage account | https://docs.microsoft.com/en-us/azure/storage/blobs/storage-blobs-overview
| vnet-{TRE_ID}-ws-XXXX	| Virtual Network | Azure TRE VNET spoke | https://microsoft.github.io/AzureTRE/azure-tre-overview/networking/
| windowsvm8f45 |	Virtual Machine | Windows VM instance for research | https://microsoft.github.io/AzureTRE/tre-templates/user-resources/guacamole-windows-vm/

!!! note
    Network resources such as Network Interfaces, Network Security Groups and Private Endpoints are not listed above.

## Running costs

The exact running costs will depend on the number of workspaces you have deployed, the workspace services you have enabled within them and the Azure Data center region.  You can use the [Azure Pricing Calculator](https://azure.microsoft.com/en-gb/pricing/calculator/) on the above services to get an indicative idea of running costs, or contact your Microsoft representative for further guidance.
