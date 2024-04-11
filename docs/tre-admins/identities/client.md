# TRE Client UX

## Name
The Client Identity is typically called `<TRE_ID> UX` within the Microsoft Entra ID Portal.

## Purpose
This identity is used by any public facing client application so that user impersonation can occur to the Core API and any Workspace Applications.

## Application Roles
This application does not have any roles defined.

## Permissions
| Name | Type* | Admin consent required |  TRE usage |
| --- | -- | -----| --------- |
|offline_access|Delegated|No|Allows the app to see and update the data you gave it access to, even when users are not currently using the app. |
|openid|Delegated|No|Allows users to sign in to the app with their work or school accounts and allows the app to see basic user profile information.|
|TRE API/user_impersonation|Delegated|No|Flow the authenticated user to the TRE API when needed.|
|Workspace API/user_impersonation|Delegated|No|Flow the authenticated user to the Workspace API when needed.|

'*' See the difference between [delegated and application permission](https://docs.microsoft.com/graph/auth/auth-concepts#delegated-and-application-permissions) types. See [Microsoft Graph permissions reference](https://docs.microsoft.com/graph/permissions-reference) for more details.

## Clients
This identity should only be used by client applications. Currently this is the React UI and the Swagger UI.

## How to create
This identity is created when you create the API. For completeness, you can run the following script
Example on how to run the script:

```bash
./devops/scripts/aad/create_api_application.sh \
    --name <TRE_ID> \
    --tre-url "https://<TRE_ID>.<LOCATION>.cloudapp.azure.com" \
    --admin-consent \
    --automation-clientid <TEST_ACCOUNT_CLIENT_ID>
```

| Argument | Description |
| -------- | ----------- |
| `--name` | The prefix of the name of the app registrations. `TRE` will give you `TRE API`. |
| `--tre-url` | Used to construct auth redirection URLs for the UI and Swagger app. Use the values of the [environment variables](../environment-variables.md) `TRE_ID` and `LOCATION` in the URL. Reply URL for the localhost, `http://localhost:8000/api/docs/oauth2-redirect`, will be added by default. |
| `--admin-consent` | Grants admin consent for the app registrations. This is required for them to function properly, but requires Microsoft Entra ID admin privileges. |
| `--automation-clientid` | This is an optional parameter but will create an application with test users with permission to use the `TRE API` and `TRE Swagger UI` |
| `--reset-password` | Optional, default is 0. This flag has no relevance when creating the UX as there is no password for the Microsoft Entra ID Application. |


## Redirect URLs
The following Redirect URIs will be added to the application
* `https://<TRE ID>.<Azure location>.cloudapp.azure.com`
* `http://localhost:8000/docs/oauth2-redirect` - For local testing

## Environment Variables
| Variable | Description | Location |
| -------- | ----------- | -------- |
|SWAGGER_UI_CLIENT_ID|The Client Id|`./config.yaml`|

