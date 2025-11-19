# Guacamole Service bundle

The Guacamole workspace service is a remote desktop gateway service that uses Apache Guacamole to access Virtual Machines (VMs) within Azure TRE workspaces. The service acts as a web-based remote desktop proxy, allowing users to connect to VMs through a web browser without requiring client software installation.

See: [https://guacamole.apache.org/](https://guacamole.apache.org/)

## Authentication to VMs via Apache Guacamole in Azure TRE

The Guacamole workspace service uses a multi-step authentication and authorization process to broker access to Virtual Machines (VMs):

- **Initial Authentication**: Users authenticate to Guacamole using OIDC (OpenID Connect) via Azure Entra ID (Azure AD) mediated by OAuth2 Proxy.

- **Token Validation**: The Guacamole extension receives and validates an OIDC token from the OAuth2 Proxy extension after the user has authenticated via Azure Entra ID, ensuring workspace roles are present in the token.

- **VM Discovery**: The extension queries the TRE API (`/api/workspaces/{workspace_id}/workspace-services/{service_id}/user-resources`) to fetch the list of VMs the authenticated user may access based on their permissions.

- **Credential Injection**: When a connection request is made to a specific VM, the extension:
  - Retrieves VM credentials from Azure Key Vault using the managed identity
  - Extracts the username and password from the secret named `{hostname}-admin-credentials`
  - Transparently injects these credentials into the Guacamole connection configuration
  - The user never sees or handles these credentials directly


- **Secure Access**: This approach works for both internal and external (guest) users, regardless of whether native Azure AD login to the VM OS is configured.

All access is brokered via the TRE API and local VM credentials are managed through Azure Key Vault, supporting users who may not have direct accounts on the VM OS or direct Azure AD login capability.

### OAuth2 Proxy Integration

The authentication system uses [OAuth2_Proxy](https://github.com/oauth2-proxy/oauth2-proxy) which is a reverse proxy and static file server that handles authentication using Providers to validate accounts by email, domain or group.
### Guacamole Authorization Extension

The extension is built (maven) and is placed inside the extension directory. Guacamole tries to authorize using all the given extensions.

Read more [here](https://guacamole.apache.org/doc/gug/guacamole-ext.html).

## Firewall Rules

Please be aware that the following Firewall rules are opened for the workspace when this service is deployed:

Service Tags:

- AzureActiveDirectory

## Prerequisites

- [A base workspace bundle installed](../workspaces/base.md)
