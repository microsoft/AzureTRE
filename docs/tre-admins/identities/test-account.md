# TRE Automation Admin Application

## Name
The Automation Application is typically called `<TRE_ID> Automation Admin App` within the AAD Portal.

## Purpose
This application is used to authorize end-to-end test scenarios.


!!! note
    - This app registration is only needed and used for **testing**


## Application Roles
This application does not have any roles defined.

## Permissions
| Name | Type* | Admin consent required |  TRE usage |
| --- | -- | -----| --------- |
|TRE API / TREAdmin|Application|Yes|This allows this application to authenticate as a TRE Admin for running the tests locally and the E2E in the build.|

'*' See the difference between [delegated and application permission](https://docs.microsoft.com/graph/auth/auth-concepts#delegated-and-application-permissions) types. See [Microsoft Graph permissions reference](https://docs.microsoft.com/graph/permissions-reference) for more details.

## Clients
This application is used locally to automatically register bundles against the API and is the user that runs the E2E locally and in the Build.

## Environment Variables
| Variable | Description | Location |
| -------- | ----------- | -------- |
|TEST_ACCOUNT_CLIENT_ID|The Client Id|`./templates/core/.env`|
|TEST_ACCOUNT_CLIENT_SECRET|The client secret|`./templates/core/.env`|

## How to create
Example on how to run the script:

```bash
./scripts/aad/aad-app-reg.sh \
  --name "${TRE_ID}" \
  --tre-url "https://${TRE_ID}.${LOCATION}.cloudapp.azure.com" \
  --admin-consent --automation-account
```

| Argument | Description |
| -------- | ----------- |
| `--name` | The prefix of the name of the app registrations. `TRE` will give you `TRE API`. |
| `--tre-url` | Used to construct auth redirection URLs for the UI and Swagger app. Use the values of the [environment variables](./environment-variables.md) `TRE_ID` and `LOCATION` in the URL. Reply URL for the localhost, `http://localhost:8000/api/docs/oauth2-redirect`, will be added by default. |
| `--admin-consent` | Grants admin consent for the app registrations. This is required for them to function properly, but requires AAD admin privileges. |
| `--automation-account` | This is an optional parameter but will create an application with a test user with permission to use the `TRE API` and `TRE Swagger UI` |

### Create this application from the portal (optional)
To create an application registration for automation, open the Azure Active Directory tenant for your TRE in the portal and navigate to "App Registrations".
Click "New registration" as shown in the image below.

![Screenshot of Azure portal showing "New registration" in Azure Active Directory](../../assets/tre-automation-new-app-registration.png)

Enter a name for the application registration and click "Register".

![Screenshot of Azure portal showing application registration details](../../assets/tre-automation-register-application.png)

On the app registration "Overview" page, copy the "Application (client) ID" value and save it for later.

![Screenshot of Azure portal showing application ID to copy](../../assets/tre-automation-client-id.png)

Under "Manage", click on "Certificates & secrets" and then "New client secret"

![Screenshot of Azure portal showing "New client secret"](../../assets/tre-automation-new-client-secret.png)

Add a description and create the client secret. Once done, the secret value will be displayed (as shown below). Copy this value and save it for later as you cannot retrieve it again after closing this page.

![Screenshot of Azure portal showing client secret value to copy](../../assets/tre-automation-client-secret.png)

#### Add API Permissions

After creating the automation application registration, it needs to be granted permissions to access the TRE API.
Navigate to the API permissions page for the application registration and click "Add a permission"

![Screenshot of Azure portal showing "Add a permission"](../../assets/tre-automation-add-api-permission.png)

Next, click on the "My APIs" tab, and then on "TRE API"
On the "Delegated permissions" section, select "user_impersonation".

![Screenshot of Azure portal showing adding user_impersonation permission](../../assets/tre-automation-add-delegated-permission.png)

On the "Application permissions" section, select "TRE Administrators".

![Screenshot of Azure portal showing adding TRE Admin permission](../../assets/tre-automation-add-application-permission.png)

Back on the main permissions page, click on "Grant admin consent". Once done, you should see "Granted" in the "Status" column, as shown below.

![Screenshot of Azure portal showing admin consent granted](../../assets/tre-automation-admin-consent-granted.png)

### Enabling users

For a user to gain access to the system, they have to:

1. Have an identity in Azure AD
1. Be linked with an app registration and assigned a role

When these requirements are met, the user can sign-in using their credentials and use their privileges to use the API, login to workspace environment etc. based on their specific roles.

![User linked with app registrations](../../assets/aad-user-linked-with-app-regs.png)

The users can also be linked via the Enterprise application view:

![Adding users to Enterprise application](../../assets/adding-users-to-enterprise-application.png)
