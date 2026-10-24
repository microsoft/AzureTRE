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

## Upgrading to version 1.3.9

Before version 1.3.9, Gitea kept the Git repositories on the container disk of the web app. Each restart of the app deleted them, but MySQL kept their records. From version 1.3.9, the repositories are on the `gitea-data` file share. The upgrade restarts the app, so the repositories on the container disk are lost.

To keep the repositories, do these steps from a workspace VM:

1. Clone each repository that you want to keep with `git clone --mirror <repository URL>`.
2. Upgrade the workspace service.
3. In Gitea, open Site Administration, then Dashboard. Run "Delete all repositories missing their Git files".
4. Create each repository again in Gitea.
5. Push each mirror into its new repository with `git push --mirror <repository URL>`.

## Repairing a service that cannot reach its file share

Before version 1.3.8, Terraform used the file endpoint of the Gitea storage account to manage the `gitea-data` share. If a delete removed the private endpoint of the account and then failed, each later update or delete of the service fails with `executing request: Get "https://stgsvc<id>.file.core.windows.net/gitea-data?restype=share": EOF`.

If you want to delete such a service:

1. Delete the storage account `stgsvc<id>` in the workspace resource group. This deletes the Gitea data on the share.
2. Delete the workspace service again. Terraform removes the share from its state, because the account does not exist.
