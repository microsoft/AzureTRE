# Configuring Shared Services

Complete the configuration of the shared services (Nexus and Gitea) from inside of the TRE environment.

## Prepare the admin jumpbox

1. Sign in to the admin jumpbox provisioned as part of the TRE deployment using Bastion. The credentials for the jumpbox are located in the KeyVault under ```vm-<tre-id>-jumpbox-admin-credentials```
2. Download Git for Windows from [https://git-scm.com/download/win](https://git-scm.com/download/win) and install
3. Download Azure CLI from [https://aka.ms/installazurecliwindows](https://aka.ms/installazurecliwindows) and install
4. Open Git Bash
5. Login to Azure ```az login``` and set the default subscription if needed: ```az account set --subscription <subscription_id>```
6. Git clone the TRE repository: ```git clone https://github.com/microsoft/AzureTRE.git```
7. Download jq ```curl -L -o /usr/bin/jq.exe https://github.com/stedolan/jq/releases/latest/download/jq-win64.exe```

## Configure Nexus repository

1. Run the Nexus configuration script to reset the password and setup a PyPI proxy on Nexus:
```./templates/shared_services/sonatype-nexus/scripts/configure_nexus.sh -t <tre_id> -l <location>```

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
