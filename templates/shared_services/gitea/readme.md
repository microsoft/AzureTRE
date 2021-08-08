# Gitea Shared Service

As outbound access to public git repositories such as GitHub is often blocked a Git mirror may be required. Gitea can be deployed as a shared service to offer this functionality.

Documentation on Gitea can be found here: [https://docs.gitea.io/](https://docs.gitea.io/).

## Deploy

To deploy set `DEPLOY_GITEA=true` in `templates/core/.env`

## Getting Started

In order to connect to the gitea admin console use the user "giteaadmin". The user's password can be found in keyvault as gitea password.
