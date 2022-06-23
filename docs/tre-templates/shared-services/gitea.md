# Gitea Shared Service

As outbound access to public git repositories such as GitHub is often blocked a git mirror may be required. Gitea can be deployed as a shared service to offer this functionality.

Documentation on Gitea can be found here: [https://docs.gitea.io/](https://docs.gitea.io/).

## Deploy

To deploy set `DEPLOY_GITEA=true` in `templates/core/.env`

## Getting Started

Connect to the Gitea admin console `https://yourtreuri/gitea/` with the `giteaadmin` user. You can find the password in keyvault as `gitea password`.

## Network requirements

Gitea needs to be able to access the following resource outside the Azure TRE VNET via explicitly allowed [Service Tags](https://docs.microsoft.com/en-us/azure/virtual-network/service-tags-overview) or URLs.

| Service Tag / Destination | Justification |
| --- | --- |
| AzureActiveDirectory | Authorize the signed in user against Azure Active Directory. |
| AzureContainerRegistry | Pull the Gitea container image, as it is located in Azure Container Registry.  |
| (www.)github.com | Allows Gitea to mirror any repo on GitHub |
