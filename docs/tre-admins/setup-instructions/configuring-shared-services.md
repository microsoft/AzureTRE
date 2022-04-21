# Configuring Shared Services

Complete the configuration of the shared services (Nexus and Gitea) from inside of the TRE environment.

Make sure you run the following command using git bash and set your current directory as C:/AzureTRE

## Configure Nexus repository

1. Run the Nexus configuration script to reset the password and setup a PyPI proxy on Nexus:
```./templates/shared_services/sonatype-nexus/scripts/configure_nexus.sh -t <tre_id>```

## Configure Gitea repository

Note : This is a Gitea *shared service* which will be accessible from all workspaces intended for mirroring external Git repositories. A Gitea *workspace service* can also be deployed per workspace to enable Gitea to be used within a specific workspace.

By default, this Gitea instance does not have any repositories configured. You can add repositories to Gitea either by using the command line or by using the Gitea web interface.


### Command Line

1. On the jumbox, run:
```./scripts/gitea_migrate_repo.sh -t <tre_id> -g <URL_of_github_repo_to_migrate>```
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
