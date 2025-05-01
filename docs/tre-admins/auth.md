# Introduction to Authentication and Authorization

[Microsoft Entra ID](https://learn.microsoft.com/en-us/entra/fundamentals/whatis) is the backbone of Authentication and Authorization in the Trusted Research Environment. Microsoft Entra ID holds the identities of all the TRE/workspace users, including administrators, and connects the identities with applications which define the permissions for each user role.

It is common that the Azure Administrator is not necessarily the Microsoft Entra ID Administrator. Due to this, this step may have to be carried out by a different individual/team. We have automated this into a simple command, but should you wish, you can run these steps manually.

This page describes the automated Auth setup for TRE.

## Pre-requisites
The automation utilises a `make` command, which reads a few environment variables and creates the Microsoft Entra ID assets. The following values are needed to be in place before you run the creation process. (`/config.yaml`)

| Key | Description |
| ----------- | ----------- |
|TRE_ID|This is used to build up the name of the identities|
|AAD_TENANT_ID|The tenant id of where your Microsoft Entra ID identities will be placed. This can be different to the tenant where your Azure resources are created.|
| LOCATION | Where your Azure assets will be provisioned (eg. westeurope). This is used to add a redirect URI from the Swagger UI to the API Application.|
|AUTO_WORKSPACE_APP_REGISTRATION| Default of `false`. Setting this to true grants the `Application.ReadWrite.All` and `Directory.Read.All` permission to the *Application Admin* identity. This identity is used to manage other Microsoft Entra ID applications that it owns, e.g. Workspaces. If you do not set this, the identity will have `Application.ReadWrite.OwnedBy`. Further information can be found&nbsp;[here](./identities/application_admin.md).|
|AUTO_WORKSPACE_GROUP_CREATION| Set to `false` by default. Setting this to `true` grants the `Group.ReadWrite.All` permission to the *Application Admin* identity. This identity can then create security groups aligned to each applciation role. Microsoft Entra ID licencing implications need to be considered as Group assignment is a premium feature. [You can read mode about Group Assignment here](https://docs.microsoft.com/en-us/azure/architecture/multitenant-identity/app-roles#roles-using-azure-ad-app-roles).|
|AUTO_GRANT_WORKSPACE_CONSENT| Default of `false`.  Setting this to `true` will remove the need for users to manually grant consent when creating new workspaces. The identity will be granted `Application.ReadWrite.All` and `DelegatedPermissionGrant.ReadWrite.All` permissions. |

## Create Authentication assets
You can build all of the Identity assets by running the following at the command line
```bash
make auth
```
This will create five identities, and if successful will write the outputs to athentication section in `config.yaml` file. If you are building locally, these values will be used when building your TRE. If you are setting this up for CI/CD, then these values will be needed by your Build Orchestrator.

The contents of your authentication section in `config.yaml` file should contain :

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

### Using a separate Microsoft Entra ID tenant

!!! caution
    This section is only relevant it you are setting up a separate Microsoft Entra ID tenant for use.
    This is only recommended for development environments when you don't have the required permissions to register applications in Microsoft Entra ID.
    Using a separate Microsoft Entra ID tenant will prevent you from using certain Microsoft Entra ID integrated services.
    For production deployments, work with your Microsoft Entra ID administrator to perform the required registration

1. Create an Microsoft Entra ID tenant
    To create a new Microsoft Entra ID tenant, [follow the steps here](https://learn.microsoft.com/en-us/entra/identity-platform/quickstart-create-new-tenant)

1. Follow the steps outlined above. `make auth` should logon to the correct tenant. Make sure you logon back to the correct tenant before running `make all`.


## App registrations

App registrations (represented by service principals) define the various access permissions to the TRE system. There are a total of five main Applications of interest.

| Microsoft Entra ID Application | Description |
| ----------- | ----------- |
| TRE API application | This is the main application and used to secure access to the [TRE API](../tre-developers/api.md). |
| TRE UX | This is the client application that will authenticate to the TRE/Workspace APIs. |
| Application Admin | There are times when workspace services need to update the Microsoft Entra ID Application. For example, Guacamole needs to add a redirect URI to the Workspace Microsoft Entra ID Application. This identity is used to manage Microsoft Entra ID Applications. |
| Automation App | This application is created so that you can run the tests or any CI/CD capability without the need to divulge a user password. This is particularly important if your tenant is MFA enabled. |
| Workspace API | Typically you would have an application securing one or more workspaces that are created by TRE. |

Some of the applications require **admin consent** to allow them to validate users against the Microsoft Entra ID. Check the Microsoft Docs on [Configure the admin consent workflow](https://learn.microsoft.com/en-us/entra/identity/enterprise-apps/configure-admin-consent-workflow) on how to request admin consent and handle admin consent requests.

We strongly recommend that you use `make auth` to create the Microsoft Entra ID assets as this has been tested extensively. Should you wish to create these manually via the [Azure Portal](https://learn.microsoft.com/en-gb/entra/identity-platform/quickstart-register-app); more information can be found [here](./identities/auth-manual.md).

### Enabling users

For a user to gain access to the system, they have to:

1. Have an identity in Microsoft Entra ID
1. Be linked with an app registration and assigned a role

When these requirements are met, the user can sign-in using their credentials and use their privileges to use the API, login to workspace environment etc. based on their specific roles.

![User linked with app registrations](../assets/aad-user-linked-with-app-regs.png)

The users can also be linked via the Enterprise application view:

![Adding users to Enterprise application](../assets/adding-users-to-enterprise-application.png)
