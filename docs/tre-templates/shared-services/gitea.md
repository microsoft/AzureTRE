# Gitea Shared Service

As outbound access to public git repositories such as GitHub is often blocked a git mirror may be required. Gitea can be deployed as a shared service to offer this functionality.

Documentation on Gitea can be found here: [https://docs.gitea.io/](https://docs.gitea.io/).

## Deploy

To deploy this shared service you should use the UI (or the API) to issue a request. If you don't see the option available for this specific template make sure it has been built, published and registered by the TRE Admin.

## Getting Started

Connect to the Gitea admin console `https://yourtreuri/gitea/` with the `giteaadmin` user. You can find the password in keyvault as `gitea password`.

## Configuring repositories

By default, this Gitea instance does not have any repositories configured. You can add repositories to Gitea either by using the command line or by using the Gitea web interface.

### Command Line

Make sure you run the following commands using git bash and set your current directory as C:/AzureTRE.

1. On the jumbox, run:
```./templates/workspace_services/gitea/gitea_migrate_repo.sh -t <tre_id> -g <URL_of_github_repo_to_migrate>```
1. If you have issues with token or token doesn't work, you can reset the token by setting it's value to null in Key Vault:
```az keyvault secret set --name gitea-<tre-id>-admin-token --vault-name kv-<tre-id> --value null```

### Gitea Web Interface

1. on the jumbox, open Edge and go to:
```https://gitea-<TRE_ID>.azurewebsites.net/```
1. Authenticate yourself using username ```giteaadmin``` and the secret ```<gitea-TRE_ID-administrator-password>``` stored in the keyvault,
1. Add the repository of your choice

### Verify can access the mirrored repository

From a virtual machine within a workspace:
- Command line: ```git clone https://gitea-<TRE_ID>.azurewebsites.net/giteaadmin/<NameOfrepository>```
- Gitea Web Interface: ```https://gitea-<TRE_ID>.azurewebsites.net/```

## Network requirements

Gitea needs to be able to access the following resource outside the Azure TRE VNET via explicitly allowed [Service Tags](https://docs.microsoft.com/en-us/azure/virtual-network/service-tags-overview) or URLs.

| Service Tag / Destination | Justification |
| --- | --- |
| AzureActiveDirectory | Authorize the signed in user against Microsoft Entra ID. |
| AzureContainerRegistry | Pull the Gitea container image, as it is located in Azure Container Registry.  |
| (www.)github.com | Allows Gitea to mirror any repo on GitHub |

## Upgrading to version 1.0.0

Migrating existing Gitea services to the major version 1.0.0 is not currently supported. This is due to the breaking change in the Terraform to migrate from the deprecated mysql_server to the new mysql_flexible_server.
