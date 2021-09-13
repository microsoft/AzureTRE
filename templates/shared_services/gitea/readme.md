# Gitea Shared Service

As outbound access to public git repositories such as GitHub is often blocked a Git mirror may be required. Gitea can be deployed as a shared service to offer this functionality.

Documentation on Gitea can be found here: [https://docs.gitea.io/](https://docs.gitea.io/).

## Deploy

To deploy set `DEPLOY_GITEA=true` in `templates/core/.env`

## Getting Started

In order to connect to the gitea admin console use the user "gitea_admin". The user's password can be found in keyvault as gitea password.

## Network requirements

To be able to run the Gitea Shared Service it need to be able to acccess the following resource outside the Azure TRE VNET via explicit allowed [Service Tags](https://docs.microsoft.com/en-us/azure/virtual-network/service-tags-overview) or URLs.

| Service Tag / Destionation | Justification |
| --- | --- |
| AzureActiveDirectory | Authorize the signed in user against Azure Active Directory. |
| AzureContainerRegistry | Pull the Gitea container image, as it is located in Azure Container Registry.  |
| AzureMonitor | Forwards tracing an logs to central location for troubleshooting. |
| (www.)github.com | Allows Gitea to mirror any repo on GitHub |
