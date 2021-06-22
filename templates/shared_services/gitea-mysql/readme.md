# Gitea Shared Service

As outbound access to public git repositories such as GitHub is often blocked a Git mirror may be required. Gitea can be deployed as a shared service to offer this functionality.

## Deploy

To deploy run:

```cmd
make terraform-deploy DIR=./templates/shared_services/gitea-mysql
```
