# Gitea Workspace Service

See: [https://gitea.io/](https://gitea.io)

## Firewall Rules

The Gitea worskpace service needs outbound access to:

- AzureActiveDirectory
- Azure AD CDN - https://aadcdn.msftauth.net

## Prerequisites

- [A base workspace deployed](../workspaces/base.md)

- The Gitea workspace service container image needs building and pushing:

  `make build-gitea-workspace-service-image push-gitea-workspace-service-image`

## Gitea Workspace Service Configuration

When deploying a Gitea Workspace service the following properties need to be configured.

| Property |  Description |
| -------- |  ----------- |
| `openid_client_id` | Valid client ID of the Workspace App Registration. |
| `openid_client_secret` | Valid client secret of the Workspace App Registration. |
| `openid_authority` | Valid authority of the OpenID service, such as `https://login.microsoftonline.com/{tenant_id}/v2.0` |

Once the service is deployed a redirect URL will need adding to the Azure AD app registration in the format: `https://<gitea_url>/user/oauth2/oidc/callback`

## Authenticating to Gitea and setting up a local username and password

1. Navigate to the Gitea workspace service and from the menu click the `Sign in` button.
2. Click sign in with OpenID button and sign in with the same credentials used to access the workspace.
3. Once succesfully signed in choose a username.
4. Navigate to the user settings and under the account tab set a password for your account( `https://<gitea_url>/user/settings/account` ). This username and passowrd should be used to authenticate against Gitea when carrying out git operations.
