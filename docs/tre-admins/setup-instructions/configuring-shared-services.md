# Configuring Shared Services

Complete the configuration of the shared services (Nexus and Gitea) from inside of the TRE environment:

## Prepare the admin jumpbox

1. Sign in to the admin jumpbox provisioned as part of the TRE deployment using Bastion. The credentials for the jumpbox are located in the KeyVault under "vm-<tre-id>-jumpbox-admin-credentials"
2. Download Git for Windows from [https://git-scm.com/download/win](https://git-scm.com/download/win) and install
3. Download Azure CLI from [https://aka.ms/installazurecliwindows](https://aka.ms/installazurecliwindows) and install
4. Open Git Bash
5. Login to Azure ```az login```
6. Git clone the TRE repository: ```git clone https://github.com/microsoft/AzureTRE.git```
7. Download jq ```curl -L -o /usr/bin/jq.exe https://github.com/stedolan/jq/releases/latest/download/jq-win64.exe```

## Configure Nexus repository

1. Run the Nexus configuration script to reset the password and setup a PyPI proxy on Nexus:
```./scripts/config_nexus.sh -t <tre_id>```

## Configure Gitea repository

1. Migrate the required repositories to Gitea by running:
```./scripts/gitea_migrate_repo.sh -t <tre_id> -g <URL_of_github_repo_to_migrate>```
