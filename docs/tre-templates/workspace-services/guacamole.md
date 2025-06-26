# Guacamole Service bundle

The Guacamole workspace service is a remote desktop gateway service that uses Apache Guacamole to access Virtual Machines (VMs) within Azure TRE workspaces. The service acts as a web-based remote desktop proxy, allowing users to connect to VMs through a web browser without requiring client software installation.

See: [https://guacamole.apache.org/](https://guacamole.apache.org/)

## Authentication to VMs via Apache Guacamole in Azure TRE

The Guacamole workspace service uses a multi-step authentication and authorization process to broker access to Virtual Machines (VMs):

- **Initial Authentication**: Users authenticate to Guacamole using OIDC (OpenID Connect) via Azure Entra ID (Azure AD), typically mediated by OAuth2 Proxy.

- **Token Validation**: The Guacamole extension receives and validates the user's token, ensuring required roles/claims are present (WorkspaceOwner, WorkspaceResearcher, or AirlockManager).

- **VM Discovery**: The extension queries the TRE API to fetch the list of VMs the authenticated user may access based on their permissions.

- **Credential Injection**: When the user connects to a VM, the extension fetches the VM credentials (username and password) from the TRE API (sourced from Azure Key Vault) and transparently injects these into the Guacamole connection configuration. The user never sees these credentials directly.

- **Secure Access**: This approach works for both internal and external (guest) users, regardless of whether native Azure AD login to the VM OS is configured.

All access is brokered via the TRE API and local VM credentials are managed through Azure Key Vault, supporting users who may not have direct accounts on the VM OS or direct Azure AD login capability.

### Detailed Authentication Flow

The TRE Authorization extension implements the following detailed authentication process:

1. **Token Reception**: Receives and validates an OIDC token from the OAuth2 Proxy extension after the user has authenticated via Azure Entra ID.

2. **Role Validation**: Validates that the token contains the required `roles` claim with at least one of the following roles:
   - `WorkspaceOwner`
   - `WorkspaceResearcher`
   - `AirlockManager`

3. **VM Discovery**: Calls the TRE API (`/api/workspaces/{workspace_id}/workspace-services/{service_id}/user-resources`) to get the list of VMs the authenticated user may access.

4. **Credential Injection**: When a connection request is made to a specific VM, the extension:
   - Retrieves VM credentials from Azure Key Vault using the managed identity
   - Extracts the username and password from the secret named `{hostname}-admin-credentials`
   - Transparently injects these credentials into the Guacamole connection configuration
   - The user never sees or handles these credentials directly

### Security Features

- **Zero-Trust Access**: Users never have direct access to VM credentials
- **API-Mediated Authorization**: All access decisions are made through the TRE API
- **External User Support**: Functions with guest users who may not have Azure AD accounts on the VM OS
- **Credential Rotation**: VM credentials are managed centrally in Azure Key Vault and can be rotated without user impact

### OAuth2 Proxy Integration

The authentication system uses [OAuth2_Proxy](https://github.com/oauth2-proxy/oauth2-proxy) which is a reverse proxy and static file server that handles authentication using Providers to validate accounts by email, domain or group.

- The main configuration is controlled by the runtime arguments in the OAuth2 Proxy service
- The Guacamole auth extension uses the generic provider (OIDC) since the Azure provider has known issues
- Important configuration includes:
  - `--insecure-oidc-allow unverified-email true`
  - `--oidc-groups-claim "roles"`

These settings were added to address [OAuth2 Proxy issue #1680](https://github.com/oauth2-proxy/oauth2-proxy/issues/1680).

## Firewall Rules

Please be aware that the following Firewall rules are opened for the workspace when this service is deployed:

Service Tags:

- AzureActiveDirectory

## Prerequisites

- [A base workspace bundle installed](../workspaces/base.md)

## Guacamole Workspace Service Configuration

When deploying a Guacamole service into a workspace the following properties need to be configured.

### Optional Properties

| Property | Options | Description |
| -------- | ------- | ----------- |
| `guac_disable_copy` | `true`/`false` (Default: `true`) | Disable Copy functionality |
| `guac_disable_paste` | `true`/`false` (Default: `false`) | Disable Paste functionality" |
| `guac_enable_drive` | `true`/`false` (Default: `true`) | Enable mounted drive |
| `guac_disable_download` | `true`/`false` (Default: `true`) | Disable files download |
| `guac_disable_upload` | `true`/`false` (Default: `true`) | Disable files upload |
| `is_exposed_externally` | `true`/`false` (Default: `true`) | Is the Guacamole service exposed outside of the vnet |
