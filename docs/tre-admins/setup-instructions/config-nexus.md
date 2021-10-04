# Configuring Nexus repository

If you have deployed Sonatype Nexus (RepoManager), you will need to complete the configuration steps from inside of the TRE environment.

1. Sign in to the admin jumpbox provisioned as part of the TRE deployment using Bastion. The credentials for the jumpbox are located in the KeyVault under "vm-<tre-id>-admin-credentials"
2. Git clone the TRE repository: ```git clone https://github.com/microsoft/AzureTRE.git```
3. Run ```./scripts/config_nexus.sh```
