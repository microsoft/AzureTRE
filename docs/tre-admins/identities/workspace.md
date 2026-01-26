# Workspace Applications

## Purpose
Access to workspaces is also controlled using app registrations - one per workspace. The configuration of the app registration depends on the nature of the workspace, but this section covers the typical minimum settings.

## Application Roles

| Display name | Description | Allowed member types | Value |
| --- | --- | --- | --- |
| Workspace Owner | Provides workspace owners access to the Workspace. | Users/Groups,Applications | `WorkspaceOwner` |
| Workspace Researcher | Provides researchers access to the Workspace. | Users/Groups,Applications | `WorkspaceResearcher` |
| Airlock Manager | Provides airlock managers access to the Workspace and ability to review airlock requests. | Users/Groups,Applications | `AirlockManager` |

## Microsoft Graph Permissions

| Name | Type* | Admin consent required | TRE usage |
| --- | --- | --- | --- |
| email | Delegated | No | Used to read the user's email address when creating TRE resources |
| openid | Delegated | No | Allows users to sign in to the app with their work or school accounts and allows the app to see basic user profile information. |
| profile | Delegated | No | Used to read the user's profile when creating TRE resources |

'*' See the difference between [delegated and application permission](https://docs.microsoft.com/graph/auth/auth-concepts#delegated-and-application-permissions) types. See [Microsoft Graph permissions reference](https://docs.microsoft.com/graph/permissions-reference) for more details.

## Clients
This identity should only be used by the API Application.

## How to create
There are two mechanisms for creating Workspace Applications
- Manually by your Microsoft Entra ID Tenant Admin (default)
- Automatically by TRE. Please see this [guide](./application_admin.md) if you wish this to be automatic.

Example on how to run the script:

```bash
  ./devops/scripts/aad/create_workspace_application.sh \
    --name "${TRE_ID} - workspace 11" \
    --application-admin-clientid "${APPLICATION_ADMIN_CLIENT_ID}"
```


| Argument | Description |
| -------- | ----------- |
| `--name` | The name of the application. This will be suffixed with 'API' by the script. |
| `--application-admin-clientid` | This is a required parameter , and should be a client id that will be added to the Owners of the Microsoft Entra ID Application so that it can be administered within TRE. |

## Comments
When the Workspace Microsoft Entra ID app is registered by running `make auth`, the `Workspace Scope Id` is the same as the Client Id. When the Workspace Microsoft Entra ID app is created by the base workspace, the `Workspace Scope Id` will be in this format `api://<TRE_ID>_ws_<WORKSPACE_SHORT_IDENTIFIER>`
