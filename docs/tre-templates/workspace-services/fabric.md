# Microsoft Fabric Workspace Service

See: [https://learn.microsoft.com/en-us/fabric/](https://learn.microsoft.com/en-us/fabric/)

This workspace service provisions a dedicated Microsoft Fabric environment within a TRE workspace, including:

- **Fabric Capacity** — an Azure resource providing compute power (configurable SKU from F2 to F2048)
- **Fabric Workspace** — a collaborative analytics environment assigned to the capacity
- **Default Lakehouse** — a pre-provisioned Lakehouse with schema support enabled
- **Workspace-level Private Link** — inbound private endpoint so workspace VMs access Fabric over the private network
- **Managed Private Endpoints** — outbound private endpoints from Fabric to the workspace shared storage account (blob + DFS)

## Network Architecture

All traffic between the TRE workspace and Fabric stays on the private network:

- **Inbound (workspace → Fabric):** A workspace-level private endpoint is created in `ServicesSubnet` using `Microsoft.Fabric/privateLinkServicesForFabric`. DNS resolves via `privatelink.fabric.microsoft.com` zone linked to the workspace VNet.
- **Outbound (Fabric → storage):** Managed private endpoints connect the Fabric workspace to the workspace's shared ADLS Gen2 storage account for both blob and DFS access.
- **Firewall rules:** Application rules allow workspace VMs to reach a minimal set of Fabric portal, API and sign-in hosts (e.g. `app.fabric.microsoft.com`, `api.fabric.microsoft.com`, `login.microsoftonline.com`) and network rules allow access to the `AzureActiveDirectory` service tag for authentication. Multi-tenant wildcards such as `*.fabric.microsoft.com`, `*.powerbi.com` and `*.analysis.windows.net` are deliberately not allowed, as they would let researchers send data to Fabric or Power BI resources in other tenants. Any additional hosts required in your environment should be reviewed and added as explicit FQDNs. To also prevent sign-in to other tenants via the allowed hosts, consider [Microsoft Entra tenant restrictions](https://learn.microsoft.com/en-us/entra/external-id/tenant-restrictions-v2).

## Prerequisites

- [A base workspace bundle installed](../workspaces/base.md)
- **Fabric must be enabled at the tenant level** by a Fabric Administrator:
    1. Go to the [Fabric Admin Portal](https://app.fabric.microsoft.com/admin-portal)
    2. Navigate to **Tenant Settings** → **Users can create Fabric items**
    3. Enable this setting

    !!! warning
        This step **cannot be automated** via Terraform or APIs. It must be performed manually before deploying this workspace service.

- **Service principals must be allowed to use Fabric APIs** in the [Admin Portal](https://app.fabric.microsoft.com/admin-portal) under **Tenant Settings** → **Developer Settings**:

    | Setting | Required | Status needed |
    | ------- | -------- | ------------- |
    | **Service principals can call Fabric public APIs** | Yes | Enabled |
    | **Service principals can create workspaces, connections, and deployment pipelines** | Yes | Enabled |

    Either apply to the entire organization, or add a security group containing the resource processor VMSS managed identity.

    !!! warning
        Without these settings, managed identities and service principals cannot create Fabric workspaces or call the Fabric API, even if they have the Fabric Administrator Entra ID role.

- **The following Fabric tenant settings must be enabled** by a Fabric Administrator in the [Admin Portal](https://app.fabric.microsoft.com/admin-portal) under **Tenant Settings** → **Network Security**:

    | Setting | Required for |
    | ------- | ------------ |
    | **Configure workspace-level inbound network rules** | Workspace-level private endpoint (inbound access from workspace VMs to Fabric) |
    | **Configure workspace-level outbound network rules** | Managed private endpoints (outbound access from Fabric to workspace storage) |

    !!! tip
        The **Configure workspace IP firewall rules** setting is optional for this service since access is controlled via private endpoints rather than IP rules.

- **Tenant-level Private Link and public access blocking must be configured** by a Fabric Administrator to prevent data exfiltration:

    1. Go to the [Fabric Admin Portal](https://app.fabric.microsoft.com/admin-portal)
    2. Navigate to **Tenant Settings** → **Advanced networking**
    3. Enable the following settings:

    | Setting | Required for |
    | ------- | ------------ |
    | **Azure Private Link** (`AllowAccessOverPrivateLinks`) | Allows private endpoint connections to Fabric |
    | **Block Public Internet Access** (`BlockAccessFromPublicNetworks`) | Prevents access to Fabric from outside private endpoints |

    !!! warning
        **Both settings are required for data exfiltration prevention.** Without "Block Public Internet Access", users with valid credentials can access Fabric workspaces from any internet-connected device, bypassing the TRE network controls. These settings apply **tenant-wide** and cannot be scoped to individual workspaces.

    !!! note
        "Azure Private Link" must be enabled **before** "Block Public Internet Access" can be turned on. These settings cannot currently be automated via API — they must be configured manually in the Fabric Admin Portal.

- The `Microsoft.Fabric` resource provider must be registered on the Azure subscription:
    ```bash
    az provider register --namespace Microsoft.Fabric
    ```
- The **resource processor VMSS managed identity** must have the **Fabric Administrator** Entra ID role so it can call the Fabric API via MSI:
    ```bash
    PRINCIPAL_ID=$(az identity show --name id-vmss-<tre_id> --resource-group rg-<tre_id> --query principalId -o tsv)
    az rest --method POST \
      --url "https://graph.microsoft.com/v1.0/roleManagement/directory/roleAssignments" \
      --headers "Content-Type=application/json" \
      --body "{\"principalId\":\"${PRINCIPAL_ID}\",\"roleDefinitionId\":\"a9ea8996-122f-4c74-9520-8edcd192826c\",\"directoryScopeId\":\"/\"}"
    ```

## Configuration

### Required Properties

| Property | Options | Description |
| -------- | ------- | ----------- |
| `fabric_capacity_sku` | `F2`, `F4`, `F8`, `F16`, `F32`, `F64`, `F128`, `F256`, `F512`, `F1024`, `F2048` (Default: `F2`) | The SKU tier for the Fabric capacity. Larger SKUs provide more compute power but cost more. Can be changed after deployment to scale up or down. |

### Optional Properties

| Property | Options | Description |
| -------- | ------- | ----------- |
| `is_exposed_externally` | `true`/`false` (Default: `false`) | Whether the Fabric workspace is accessible from outside the workspace network |

## Managed Private Endpoint Approval

The managed private endpoints (blob and DFS) targeting the workspace storage account are created in a **Pending** state. The deployment approves them automatically, but only the connections whose request message exactly matches the one set by this workspace service. The deployment fails if a matching connection cannot be uniquely identified or is not approved, and other pending connections on the storage account are left untouched.

The identity used by the resource processor requires `Microsoft.Storage/storageAccounts/privateEndpointConnectionsApproval/action` permission on the workspace storage account.

## Restricting Public Access

Public access to the Fabric workspace is restricted at multiple levels:

### Outbound access protection (automated)

During deployment, this service uses the `fabric_workspace_network_communication_policy` Terraform resource to set the workspace [network communication policy](https://learn.microsoft.com/en-us/rest/api/fabric/core/workspaces/set-network-communication-policy) outbound public access to **Deny**. This is applied after the Fabric managed VNet has been provisioned. This prevents Fabric workloads from making outbound connections to public endpoints, blocking data exfiltration from the workspace.

!!! note
    Inbound public access is left as **Allow** because the TRE resource processor (VMSS) needs to manage the workspace via the Fabric API from core infrastructure. Users inside workspace VMs still access Fabric exclusively through the private endpoint, enforced by the workspace VNet and firewall rules.

### Tenant-level (manual prerequisite)

To fully prevent data exfiltration, you **must** also enable tenant-level private link and block public access (see [Prerequisites](#prerequisites)). The two tenant-level settings work together:

1. **Azure Private Link** — enables private endpoint connections to Fabric
2. **Block Public Internet Access** — ensures Fabric is **only** accessible via private endpoints

These are configured in the [Fabric Admin Portal](https://app.fabric.microsoft.com/admin-portal) → **Tenant Settings** → **Advanced networking**.

!!! warning
    These settings are **tenant-wide**. Enabling "Block Public Internet Access" will affect all Fabric workspaces in the tenant, not just TRE-managed ones.

See [Fabric Private Links](https://learn.microsoft.com/en-us/fabric/security/security-private-links-use) for details.

!!! note
    There is currently no Terraform resource or API to automate the tenant-level private link settings. They must be configured manually in the Fabric Admin Portal.

## Accessing Workspace Storage from Fabric

The workspace's shared ADLS Gen2 storage account is accessible from Fabric via the managed private endpoints provisioned by this service. Researchers can read and write data using Spark notebooks with `abfss://` URIs — see [Access Azure Data Lake Storage Gen2 from Fabric](https://learn.microsoft.com/en-us/fabric/onelake/access-onelake-shortcuts#azure-data-lake-storage-gen2).

!!! note
    OneLake shortcuts to ADLS Gen2 are **not supported** through managed private endpoints ([details](https://learn.microsoft.com/en-us/fabric/security/security-managed-private-endpoints-overview)). Use Spark notebooks or Data Pipelines to load data from workspace storage into the Lakehouse instead.

## Known Limitations

- **OneLake shortcuts to ADLS Gen2 do not work through managed private endpoints.** This is a [documented Fabric limitation](https://learn.microsoft.com/en-us/fabric/security/security-managed-private-endpoints-overview). Spark notebooks and other compute workloads can access storage directly via the managed PEs.
- **Newly created capacity** may take up to 24 hours before the workspace private endpoint is fully functional.
- Fabric capacity is billed per hour. Consider scaling down to F2 when not in active use.

## References

- [Microsoft Fabric Terraform Provider](https://registry.terraform.io/providers/microsoft/fabric/latest/docs)
- [Fabric Terraform Quickstart](https://github.com/microsoft/fabric-terraform-quickstart)
- [Workspace-level Private Links](https://learn.microsoft.com/en-us/fabric/security/security-private-links-overview)
- [Managed Private Endpoints](https://learn.microsoft.com/en-us/fabric/security/security-managed-private-endpoints-overview)
- [Fabric Admin Portal Settings](https://learn.microsoft.com/en-us/fabric/admin/fabric-switch)
