# Authentication and authorization

[Azure Active Directory (AAD)](https://docs.microsoft.com/en-us/azure/active-directory/fundamentals/active-directory-whatis) is the backbone of Authentication and Authorization in the Trusted Research Environment.

AAD holds the identities of all the TRE/workspace users, including administrators, and connects the identities with applications which define the permissions for each user role.

## Pre-requisites
The following values are needed to be in place to run the script. (`/templates/core/.env`)

| Key | Description |
| ----------- | ----------- |
|TRE_ID|This is needed to build up the redirect URI for the Swagger App|
|AAD_TENANT_ID|The tenant id of where your AAD identities will be placed. This can be different to the tenant where your Azure resources are created.|
|AUTO_WORKSPACE_APP_REGISTRATION| Default of `false`. Setting this to true grants the `Application.ReadWrite.All` permission to the API AAD Application. This allows it to create other AAD applications, e.g. Workspaces.

## Create Authentication assets
You can build all of the Identity assets by running the following at the command line
```bash
make auth
```
Follow the instructions and prompts in the script. It will ask you to confirm at various stages, so don't go and make a coffee! This will create the 4 parts of authentication outlined below, and if succesful you will not need to do anything apart from copy some values into `/templates/core/.env`. The details below are for your understanding.

### Using a separate Azure Active Directory tenant

!!! caution
    This section is only relevant it you are setting up a separate Azure Active Directory tenant for use.
    This is only recommended for development environments when you don't have the required permissions to create the necessary Azure Active Directory registrations.
    Using a separate Azure Active Directory tenant will prevent you from using certain Azure Active Directory integrated services.
    For production deployments, work with your Azure Active Directory administrator to perform the required registration

1. Create an Azure Active Directory tenant
    To create a new Azure Active Directory tenant, [follow the steps here](https://docs.microsoft.com/en-us/azure/active-directory/develop/quickstart-create-new-tenant)

1. Follow the steps outlined above. `make auth` should logon to the correct tenant. Make sure you logon back to the correct tenant before running `make all`.


## App registrations

App registrations (represented by service principals) define the various access permissions to the TRE system. There are a total of four main Applications of interest.

| AAD Application | Description |
| ----------- | ----------- |
| TRE API application | This is the main application and used to authenticate access to the [TRE API](../tre-developers/api.md). |
| TRE Swagger UI | This is used to authenticate identities who wish to use the Swagger UI |
| Automation App | This application is created so that you can run the  tests or any CI/CD capability. This is particularly important if your tenant is MFA enabled. |
| Workspace API | Typically you would have an application securing one or more workspaces that are created by TRE. |

Some of the applications require **admin consent** to allow them to validate users against the AAD. Check the Microsoft Docs on [Configure the admin consent workflow](https://docs.microsoft.com/en-us/azure/active-directory/manage-apps/configure-admin-consent-workflow) on how to request admin consent and handle admin consent requests.

You can create these applications manually, but `/scripts/aad/aad-app-reg.sh`  does the heavy lifting for you. Should you wish to create these manually via the [Azure Portal](https://docs.microsoft.com/azure/active-directory/develop/quickstart-register-app). The requirements are defined [below](#Manual-Deployment).

## App registration script

### TRE API, Swagger and Automation Account

The `/scripts/aad/aad-app-reg.sh` script automatically sets up the app registrations with the required permissions to run Azure TRE. It will create and configure all of the app registrations depending on the parameters. You would typically run this script twice; once for the **TRE API** and once for each **Workspace**.

Example on how to run the script:

```bash
./scripts/aad/aad-app-reg.sh \
    --name <TRE_ID> \
    --swaggerui-redirecturl https://<TRE_ID>.<Azure location>.cloudapp.azure.com/api/docs/oauth2-redirect \
    --read-write-all-permission \
    --admin-consent \
    --automation-account \
    --read-write-all-permission
```
Below is a sample where `TRE_ID` has value `mytre` and the Azure location is `westeurope`:

  ```bash
  ./scripts/aad/aad-app-reg.sh --name TRE --swaggerui-redirecturl https://mytre.westeurope.cloudapp.azure.com/api/docs/oauth2-redirect --admin-consent
  --automation-account
  ```

| Argument | Description |
| -------- | ----------- |
| `--name` | The prefix of the name of the app registrations. `TRE` will give you `TRE API` and `TRE Swagger UI`. |
| `--swaggerui-redirecturl` | The reply URL for the Swagger UI app. Use the values of the [environment variables](./environment-variables.md) `TRE_ID` and `LOCATION` in the URL. Reply URL for the localhost, `http://localhost:8000/api/docs/oauth2-redirect`, will be added by default. |
| `--admin-consent` | Grants admin consent for the app registrations. This is required for them to function properly, but requires AAD admin privileges. |
| `--automation-account` | This is an optional parameter but will create an application with test users with permission to use the `TRE API` and `TRE Swagger UI` |
| `--read-write-all-permission` | This is an optional parameter that if present will grant the Read/Write All permission to the Application. This allows it to create other applications (such as workspaces).

!!! caution
    The script will create an app password (client secret) for the **TRE API** app and the **Automation App** and tell you to copy these to the `/templates/core/.env` file. These values are only shown once, if you lose them, the script will create new secrets if run again.


You can create an automation account which will aid your development flow, if you don't want to do this you can omit the `--automation-account` switch.

If your AAD Admin is uncomfortable allowing an Application to have the permissions to create other applications then remove the `--read-write-all-permission` from the command.

You can run the script without the `--admin-consent` and ask your admin to grant consent. If you don't have permissions and just want to create a development environment then skip this step and see the steps in the "Using a separate Azure Active Directory tenant) below.

### Workspace Applications

Access to workspaces is also controlled using app registrations - one per workspace. The configuration of the app registration depends on the nature of the workspace, but this section covers the typical minimum settings.

!!! caution
    The app registration for a workspace is not created by the [API](../tre-developers/api.md). One needs to be present before using the API to provision a new workspace. If you ran `make auth`, a workspace AD application was created for you. If you wish to create another, the same script can be used to create the **Workspace Application**.

Example on how to run the script:

```bash
./scripts/aad/aad-app-reg.sh \
    --name '<TRE_ID> - Workspace 2' \
    --workspace \
    --swaggerui-clientid <SWAGGER_UI_CLIENT_ID> \
    --admin-consent \
    --automation-clientid <TEST_ACCOUNT_CLIENT_ID>
```

| Argument | Description |
| -------- | ----------- |
| `--name` | The name of the application. This will be suffixed with 'API' by the script. |
| `--workspace` | This tells the script to create you are creating a workspace app rather than the TRE API app. |
| `--swaggerui-clientid` | This value is one of the outputs when you first ran the script. It is mandatory if you use admin-consent. |
| `--admin-consent` | Grants admin consent for the app registrations. This is required for them to function properly, but requires AAD admin privileges. |
| `--automation-clientid` | This is an optional parameter but will grant the Automation App (created in step 1) permission to the new workspace app. |

!!! caution
    The script will create an app password (client secret) for the workspace and tell you to copy these to the `/templates/core/.env` file. These values are only shown once, if you lose them, the script will create new secrets if run again.


If you do not wish to create an Automation App, just remove the `--automation-clientid` from the command.

## Manual Deployment

### TRE API

The **TRE API** app registration defines the permissions, scopes and app roles for API users to authenticate and authorize API calls.

#### API permissions - TRE API

| API/permission name | Type | Description | Admin consent required | Status | TRE usage |
| ------------------- | ---- | ----------- | ---------------------- | ------ | --------- |
| Microsoft Graph/Directory.Read.All (`https://graph.microsoft.com/Directory.Read.All`) | Application* | Allows the app to read data in your organization's directory, such as users, groups and apps, without a signed-in user. | Yes | Granted for *[directory name]* | Used e.g., to retrieve app registration details, user associated app roles etc. |
| Microsoft Graph/User.Read.All (`https://graph.microsoft.com/User.Read.All`) | Application* | Allows the app to read user profiles without a signed in user. | Yes | Granted for *[directory name]* | Reading user role assignments to check that the user has permissions to execute an action e.g., to view workspaces. See `/api_app/services/aad_authentication.py`. |

*) See the difference between [delegated and application permission](https://docs.microsoft.com/graph/auth/auth-concepts#delegated-and-application-permissions) types.

See [Microsoft Graph permissions reference](https://docs.microsoft.com/graph/permissions-reference) for more details.

#### Scopes - TRE API

* `api://<Application (client) ID>/` **`user_impersonation`** - Allow the app to access the TRE API on behalf of the signed-in user

#### App roles - TRE API

| Display name | Description | Allowed member types | Value |
| ------------ | ----------- | -------------------- | ----- |
| TRE Administrators | Provides resource administrator access to the TRE. | Users/Groups,Applications | `TREAdmin` |
| TRE Users | Provides access to the TRE application. | Users/Groups,Applications | `TREUser` |

#### Authentication - TRE API

The **TRE API** app registration requires no redirect URLs defined or anything else for that matter. From a security standpoint it should be noted that public client flows should not be allowed. As the identity of the client application cannot be verified (see the image below taken from app registration authentication blade in Azure Portal).

![Allow public client flows - No](../assets/app-reg-authentication-allow-public-client-flows-no.png)

### TRE Swagger UI

**TRE Swagger UI** app registration:

* Controls the access to the Swagger UI of the TRE API
* Has no scopes or app roles defined

#### API permissions - TRE Swagger UI

| API/permission name | Type | Description | Admin consent required | Status |
| ------------------- | ---- | ----------- | ---------------------- | ------ |
| Microsoft Graph/offline_access (`https://graph.microsoft.com/offline_access`) | Delegated* | Allows the app to see and update the data you gave it access to, even when users are not currently using the app. | No | Granted for *[directory name]* |
| Microsoft Graph/openid (`https://graph.microsoft.com/openid`) | Delegated* | Allows users to sign in to the app with their work or school accounts and allows the app to see basic user profile information. | No | Granted for *[directory name]* |
| TRE API/user_impersonation (`api://<TRE API Application (client) ID>/user_impersonation`) | Delegated* | See [TRE API app registration scopes](#scopes---tre-api). | No | Granted for *[directory name]* |

*) See the difference between [delegated and application permission](https://docs.microsoft.com/graph/auth/auth-concepts#delegated-and-application-permissions) types.

#### Authentication - TRE Swagger UI

Redirect URLs:

* `https://<TRE ID>.<Azure location>.cloudapp.azure.com/docs/oauth2-redirect`
* `http://localhost:8000/docs/oauth2-redirect` - For local testing

### Workspaces

#### Authentication - Workspaces

Same as [TRE API](#authentication-tre-api).

#### API permissions - Workspaces

| API/permission name | Type | Description | Admin consent required |
| ------------------- | ---- | ----------- | ---------------------- |
| Microsoft Graph/User.Read (`https://graph.microsoft.com/User.Read`) | Delegated | Allows users to sign-in to the app, and allows the app to read the profile of signed-in users. It also allows the app to read basic company information of signed-in users. | No |
| Workspace API/user_impersonation (`api://<Workspace Scope ID>/user_impersonation`) | Delegated* | Allows the app to access the workspace API on behalf of the user | No | Granted for *[directory name]* |

When the Workspace AAD app is registered by the aad-app-reg.sh, the `Workspace Scope Id` is the same as the Client Id. When the Workspace AAD app is created by the base workspace, the `Workspace Scope Id` will be in this format `api://<TRE_ID>_ws_<WORKSPACE_SHORT_IDENTIFIER>`

#### App roles

| Display name | Description | Allowed member types | Value |
| ------------ | ----------- | -------------------- | ----- |
| Owners | Provides ownership access to workspace. | Users/Groups | `WorkspaceOwner` |
| Researchers | Provides access to workspace. | Users/Groups | `WorkspaceResearcher` |

### TRE e2e test

The **TRE Automation Admin App** registration is used to authorize end-to-end test scenarios.

!!! note
    - This app registration is only needed and used for **testing**

#### Create an application

To create an application registration for automation, open the Azure Active Directory tenant for your TRE in the portal and navigate to "App Registrations".
Click "New registration" as shown in the image below.

![Screenshot of Azure portal showing "New registration" in Azure Active Directory](../assets/tre-automation-new-app-registration.png)

Enter a name for the application registration and click "Register".

![Screenshot of Azure portal showing application registration details](../assets/tre-automation-register-application.png)

On the app registration "Overview" page, copy the "Application (client) ID" value and save it for later.

![Screenshot of Azure portal showing application ID to copy](../assets/tre-automation-client-id.png)

Under "Manage", click on "Certificates & secrets" and then "New client secret"

![Screenshot of Azure portal showing "New client secret"](../assets/tre-automation-new-client-secret.png)

Add a description and create the client secret. Once done, the secret value will be displayed (as shown below). Copy this value and save it for later as you cannot retrieve it again after closing this page.

![Screenshot of Azure portal showing client secret value to copy](../assets/tre-automation-client-secret.png)

#### Add API Permissions

After creating the automation application registration, it needs to be granted permissions to access the TRE API.
Navigate to the API permissions page for the application registration and click "Add a permission"

![Screenshot of Azure portal showing "Add a permission"](../assets/tre-automation-add-api-permission.png)

Next, click on the "My APIs" tab, and then on "TRE API"
On the "Delegated permissions" section, select "user_impersonation".

![Screenshot of Azure portal showing adding user_impersonation permission](../assets/tre-automation-add-delegated-permission.png)

On the "Application permissions" section, select "TRE Administrators".

![Screenshot of Azure portal showing adding TRE Admin permission](../assets/tre-automation-add-application-permission.png)

Back on the main permissions page, click on "Grant admin consent". Once done, you should see "Granted" in the "Status" column, as shown below.

![Screenshot of Azure portal showing admin consent granted](../assets/tre-automation-admin-consent-granted.png)

### Enabling users

For a user to gain access to the system, they have to:

1. Have an identity in Azure AD
1. Be linked with an app registration and assigned a role

When these requirements are met, the user can sign-in using their credentials and use their privileges to use the API, login to workspace environment etc. based on their specific roles.

![User linked with app registrations](../assets/aad-user-linked-with-app-regs.png)

The users can also be linked via the Enterprise application view:

![Adding users to Enterprise application](../assets/adding-users-to-enterprise-application.png)
