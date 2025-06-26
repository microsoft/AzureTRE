# Guacamole Service bundle

See: [https://guacamole.apache.org/](https://guacamole.apache.org/)

## Authentication to VMs via Apache Guacamole in Azure TRE

The Guacamole workspace service provides secure remote access to Virtual Machines (VMs) through a sophisticated authentication and authorization process that works seamlessly for both internal and external users:

- **Initial Authentication**: Users authenticate to Guacamole using OIDC (OpenID Connect) via Azure Entra ID (Azure AD), typically mediated by OAuth2 Proxy.

- **Token Validation**: The Guacamole extension receives and validates the user's token, ensuring required roles/claims are present (WorkspaceOwner, WorkspaceResearcher, or AirlockManager).

- **VM Discovery**: The extension queries the TRE API to fetch the list of VMs the authenticated user may access based on their permissions.

- **Credential Injection**: When the user connects to a VM, the extension fetches the VM credentials (username and password) from the TRE API (sourced from Azure Key Vault) and transparently injects these into the Guacamole connection configuration. The user never sees these credentials directly.

- **Secure Access**: This approach allows both internal and external (guest) users to access VMs securely, regardless of whether native Azure AD login to the VM OS is supported.

All access is brokered via the TRE API and local VM credentials are managed securely, enabling VM access for users that may not have direct accounts on the VM OS or direct Azure AD login capability.

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
