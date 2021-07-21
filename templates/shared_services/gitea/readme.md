# Gitea Shared Service

As outbound access to public git repositories such as GitHub is often blocked a Git mirror may be required. Gitea can be deployed as a shared service to offer this functionality.

Documentation on Gitea can be found here: [https://docs.gitea.io/](https://docs.gitea.io/).

## Deploy

To deploy set `DEPLOY_GITEA=true` in `templates/core/.env`
