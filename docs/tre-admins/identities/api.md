# The API Identity

## Name
The API Identity is typically called `<TRE_ID> API` within the Microsoft Entra ID Portal.

## Purpose
This identity's credentials are stored in the `core` Key Vault and mandatory for the running of the Trusted Research Environment (TRE). It is required for the API Application, hosted in Azure App Service, to authenticate to Microsoft Entra ID and authorize the various operations.

## Application Roles

| Display name | Description | Allowed member types | Value |
| ------------ | ----------- | -------------------- | ----- |
| TRE Administrators | Provides resource administrator access to the TRE. | Users/Groups,Applications | `TREAdmin` |
| TRE Users | Provides access to the TRE application. | Users/Groups,Applications | `TREUser` |

## Microsoft Graph Permissions
| Name | Type* | Admin consent required |  TRE usage |
| --- | -- | -----| --------- |
| Directory.Read.All | Application | Yes | Allows the app to read directory objects (roles/permissions) in your organization's directory, such as roles and permissions, without a signed-in user. |
| User.Read.All | Application | Yes | Allows the app to read user profiles without a signed in user to check that the user has permissions to execute an action e.g., to view workspaces. See `/api_app/services/aad_authentication.py`. |
|email|Delegated|No|Used to read the user's email address when creating TRE resources|
|openid|Delegated|No|Allows users to sign in to the app with their work or school accounts and allows the app to see basic user profile information.|
|profile|Delegated|No|Used to read the user's profile when creating TRE resources|


'*' See the difference between [delegated and application permission](https://docs.microsoft.com/graph/auth/auth-concepts#delegated-and-application-permissions) types. See [Microsoft Graph permissions reference](https://docs.microsoft.com/graph/permissions-reference) for more details.

## Clients
This identity should only be used by the API Application.

## How to create
Example on how to run the script:

```bash
./devops/scripts/aad/create_api_application.sh \
    --name <TRE_ID> \
    --tre-url "https://<TRE_ID>.<LOCATION>.cloudapp.azure.com" \
    --admin-consent \
    --automation-clientid <TEST_ACCOUNT_CLIENT_ID>
```
Below is a sample where `TRE_ID` has value `mytre`:

  ```bash
  ./devops/scripts/aad/create_api_application.sh --name mytre --admin-consent \
  --tre-url "https://mytre_6.westeurope.cloudapp.azure.com" --automation-clientid 176c2f5d-xxxx-xxxx-xxxx-68a5c30f354d
  ```

| Argument | Description |
| -------- | ----------- |
| `--name` | The prefix of the name of the app registrations. `TRE` will give you `TRE API`. |
| `--tre-url` | Used to construct auth redirection URLs for the UI and Swagger app. Use the values of the [environment variables](../environment-variables.md) `TRE_ID` and `LOCATION` in the URL. Reply URL for the localhost, `http://localhost:8000/api/docs/oauth2-redirect`, will be added by default. |
| `--admin-consent` | Grants admin consent for the app registrations. This is required for them to function properly, but requires Microsoft Entra ID admin privileges. |
| `--automation-clientid` | This is an optional parameter but will grant TREAdmin permission to the Service Principal of the Automation Admin.|
| `--reset-password` | Optional, default is 0. When run in a headless fashion, 1 is passed in to always reset the password. |


!!! caution
    The script will create an app password (client secret) for the **TRE API** app and the **Automation App** and write them to `/config.yaml` file. These values are only shown once, if you lose them, the script will create new secrets if run again.


You can create an automation account which will aid your development flow, if you don't want to do this you can omit the `--automation-clientid` switch.

You can run the script without the `--admin-consent` and ask your admin to grant consent. If you don't have permissions and just want to create a development environment then skip this step and see the steps in the "Using a separate Microsoft Entra ID tenant) below.

## Environment Variables
| Variable | Description | Location |
| -------- | ----------- | -------- |
|API_CLIENT_ID|The Client Id|`./config.yaml`|
|API_CLIENT_SECRET|The client secret|`./config.yaml`|

## Comments

The **TRE API** app registration requires no redirect URLs defined. From a security standpoint, public client flows should not be allowed. As the identity of the client application cannot be verified (see the image below taken from app registration authentication blade in Azure Portal).

![Allow public client flows - No](../../assets/app-reg-authentication-allow-public-client-flows-no.png)
