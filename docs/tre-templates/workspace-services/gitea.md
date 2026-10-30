# Gitea Workspace Service

See: [https://gitea.io/](https://gitea.io)

## Firewall Rules

The Gitea worskpace service opens outbound access to:

- AzureActiveDirectory
- Microsoft Entra ID CDN - `https://aadcdn.msftauth.net`

## Prerequisites

- [A base workspace deployed](../workspaces/base.md)

- The Gitea workspace service container image needs building and pushing:

  `make workspace_service_bundle BUNDLE=gitea`

## Authenticating to Gitea and setting up a local username and password

1. Navigate to the Gitea workspace service using the connection URI from the details tab.
2. and from the menu click the `Sign in` button.
3. Click sign in with OpenID button and sign in with the same credentials used to access the workspace.
4. Once successfully signed in choose a username.
5. Navigate to the user settings and under the account tab set a password for your account( `https://<gitea_url>/user/settings/account` ). This username and password should be used to authenticate against Gitea when carrying out git operations.

## Upgrading to version 1.0.0

Migrating existing Gitea services to the major version 1.0.0 is not currently supported. This is due to the breaking change in the Terraform to migrate from the deprecated mysql_server to the new mysql_flexible_server.

## Upgrading to version 2.0.0

Version 2.0.0 is a major version, because the upgrade needs the steps below. The TRE blocks the upgrade until you use a [force version update](../../tre-admins/upgrading-resources.md#force-version-update).

### Repositories on the file share

Before version 2.0.0, Gitea kept the Git repositories on the container disk of the web app. Each restart of the app deleted them, but MySQL kept their records. From version 2.0.0, the repositories are on the `gitea-data` file share. The upgrade restarts the app, so the repositories on the container disk are lost.
The issues, pull requests and releases stay in MySQL, and the LFS files stay on the file share.

To keep the repositories, do these steps from a workspace VM:

1. Clone each repository that you want to keep with `git clone --mirror <repository URL>`.
2. If a repository has a wiki, also clone its wiki with `git clone --mirror <wiki URL>`. The wiki URL ends in `.wiki.git` in place of `.git`.
3. Upgrade the workspace service.
4. In Gitea, open Site Administration, then Dashboard. Run "Reinitialize all missing Git repositories for which records exist".
5. Push each mirror into the same repository with `git push --mirror <repository URL>`.
6. For each wiki, create one page in Gitea. Then push the wiki mirror with `git push --mirror <wiki URL>`.

Do not run "Delete all repositories missing their Git files". This task also deletes the records of the repositories, for example their issues and pull requests.

### Secrets in the console log

Before version 2.0.0, the Gitea workspace service wrote secrets to the console log of its web app. The web app sends this log to Log Analytics, so all people who can read the Log Analytics workspace of the TRE can read these secrets:

- The client secret of the workspace application.
- The password of the Gitea admin user.
- An access token of the Gitea admin user, with the name `gitea-admin`.

If a Gitea workspace service ran an earlier version, do these steps after the upgrade:

1. Make a new client secret for the workspace application:
    - If Terraform registered the workspace application (`register_aad_application` is `true`), the client secret is a password of its service principal, not of the app registration. The Microsoft Entra admin center does not show it. Do these steps:
        1. List the passwords of the service principal with `az rest --method GET --url "https://graph.microsoft.com/v1.0/servicePrincipals(appId='<client ID>')" --query "passwordCredentials[].{keyId:keyId,hint:hint}"`.
        2. Find the password whose `hint` is the same as the first three characters of the workspace Key Vault secret `workspace-client-secret`.
        3. Remove it with `az rest --method POST --url "https://graph.microsoft.com/v1.0/servicePrincipals(appId='<client ID>')/removePassword" --body '{"keyId": "<key ID>"}'`.
        4. Update the workspace. Terraform makes a new password and writes it to `workspace-client-secret`.
    - If you registered the workspace application, add a new client secret in Microsoft Entra ID. Write the new value to the workspace Key Vault secret `workspace-client-secret`. You need a role that can set secrets and network access to the Key Vault. Then delete the old client secret.
2. Update each Guacamole and OHDSI workspace service in the workspace. These services use the version of the secret that was current when they deployed.
3. Make the Gitea web app read the new client secret from the Key Vault. Send a POST request to `https://management.azure.com/<web app resource ID>/config/configreferences/appsettings/refresh?api-version=2022-03-01`, for example with `az rest`.
4. Restart the Gitea web app. At the start, the start script gives the OIDC source the new client secret. Then it stops Gitea one time, and App Service starts it again with the new secret.
5. Sign in to Gitea as the admin user. In the user settings, open Applications and delete the access token `gitea-admin`.
6. If the people who can read Log Analytics must not get admin access to Gitea, change the password of the admin user in Gitea. Keep the new password in a safe location. The Key Vault secret `<web app name>-administrator-password` keeps the old value, because the start script does not change the password of an existing admin user.

From version 2.0.0, the start script keeps a hash of the OIDC settings on the file share. If the settings change, the script stops Gitea one time, because Gitea reads them only at its start. The first start after the upgrade also does this, because the hash does not exist yet.

## Repairing a service that cannot reach its file share

Before version 2.0.0, Terraform used the file endpoint of the Gitea storage account to manage the `gitea-data` share. If a delete removed the private endpoint of the account and then failed, each later update or delete of the service fails with `executing request: Get "https://stgsvc<id>.file.core.windows.net/gitea-data?restype=share": EOF`.

If you want to delete such a service:

1. Delete the storage account `stgsvc<id>` in the workspace resource group. This deletes the Gitea data on the share.
2. Delete the workspace service again. Terraform removes the share from its state, because the account does not exist.
