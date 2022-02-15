# Nexus Shared Service

Sonatype Nexus (RepoManager) allows users in workspaces to access external software packages securely.

Documentation on Nexus can be found here: [https://help.sonatype.com/repomanager3/](https://help.sonatype.com/repomanager3/).

## Deploy

To deploy set `DEPLOY_NEXUS=true` in `templates/core/.env`.

Nexus will be deployed as part of the main TRE terraform deployment. A configuration script needs to be run once the deployment is done. The script will:

1. Fetch the Nexus generated password from storage account.
2. Reset the default password and set a new one.
3. Store the new password in Key Vault under 'nexus-<TRE_ID>-admin-password'
4. Create an anonymous default PyPI proxy repository

## Setup and usage

1. A TRE Administrator can access Nexus though the admin jumpbox provisioned as part of the TRE deployment. The credentials for the jumpbox are located in the KeyVault under "vm-<tre-id>-jumpbox-admin-credentials"
2. A researcher can access Nexus from within the workspace by using the internal Nexus URL of: [https://nexus-<TRE_ID>.azurewebsites.net/](https://nexus-<TRE_ID>.azurewebsites.net/)
3. To fetch Python packages from the PyPI proxy, a researcher can use pip install while specifying the proxy server:

    ```bash
    pip install packagename --index-url https://nexus-<TRE_ID>.azurewebsites.net/repository/apt-pypi/simple
    ```

## Network requirements

Nexus Shared Service requires access to resources outside of the Azure TRE VNET. These are set as part of the firewall provisioning pipeline via explicit allow on [Service Tags](https://docs.microsoft.com/en-us/azure/virtual-network/service-tags-overview) or URLs.
Notice that since Nexus Shared Service is running on an App Service, the outgoing exceptions are made for the calls coming out of the Web App Subnet.

| Service Tag / Destination | Justification |
| --- | --- |
| AzureActiveDirectory | Authorize the signed in user against Azure Active Directory. |
| AzureContainerRegistry | Pull the Nexus container image, as it is located in Azure Container Registry.  |
| pypi.org | Enables Nexus to "proxy" python packages to use inside of workspaces |
