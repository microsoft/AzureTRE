# Guacamole Authorization Extension

This extension is built (maven) and is placed inside the extension directory.
Guacamole tries to authorize using all the given extensions.
Read more [here](https://guacamole.apache.org/doc/gug/guacamole-ext.html).

## TRE Authorization extension

This extension provides secure authentication and authorization for VM access in Azure TRE. It works in the following manner:

### Authentication Flow

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
- **External User Support**: Enables secure VM access for guest users who may not have Azure AD accounts on the VM OS
- **Credential Rotation**: VM credentials are managed centrally in Azure Key Vault and can be rotated without user impact

## OAuth2 Proxy


- The extention uses [OAuth2_Proxy](https://github.com/oauth2-proxy/oauth2-proxy) which is a reverse proxy and static file server that provides authentication using Providers to validate accounts by email, domain or group.
- The current version that is being used is **7.4.0.**
- The main file that controls the behavior of the oauth2 proxy is the [run](/workspaces/AzureTRE/templates/workspace_services/guacamole/guacamole-server/docker/services/oauth/run) file, which contains all the runtime arguments.
- Some important notes on the way we use the oauth2 proxy:
  - Guacamole auth extention uses the generic provider (oidc) since the Azure provider is broken in the proxy repository.
  - When upgraded to version 7.4.0, \
  `--insecure-oidc-allow unverified-email true,
   --oidc-groups-claim "roles"` were added becaue of this following [issue](https://github.com/oauth2-proxy/oauth2-proxy/issues/1680).
