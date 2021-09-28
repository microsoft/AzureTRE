# Nexus Shared Service

This service allows users in workspaces to access external software packages securely by relying on Sonatype Nexus (RepoManager).
Documentation on Nexus can be found here: [https://help.sonatype.com/repomanager3/](https://help.sonatype.com/repomanager3/).

## Deploy

To deploy set `DEPLOY_NEXUS=true` in `templates/core/.env`.

Nexus will be deployed as part of the main TRE terraform deployment. A configuration script will be executed once the container is running to:

1. Reset the default password and set a new one.
2. Store the new password in Key Vault under 'nexus-<TRE_ID>-admin-password'
3. Create an anonymous default PyPI proxy repository

## Setup and usage  

1. A TRE Administrator can access Nexus from the public network through the application gateway on: [https://<TRE_ID>.<REGION>.cloudapp.azure.com/nexus/](https://<TRE_ID>.<REGION>.cloudapp.azure.com/nexus/) using the password found in the Key Vault
2. A researcher can access Nexus from within the workspace by using the internal Nexus URL of: [https://nexus-<TRE_ID>.azurewebsites.net/](https://nexus-<TRE_ID>.azurewebsites.net/)
3. To fetch Python packages from the PyPI proxy, a researcher can use pip install while specifying the proxy server:

    ```bash
    pip install packagename --index-url https://nexus-<TRE_ID>.azurewebsites.net/repository/pypi-proxy-repo/simple
    ```

## Network requirements

Nexus Shared Service requires access to resources outside of the Azure TRE VNET. These are set as part of the firewall provisioning pipeline via explicit allow on [Service Tags](https://docs.microsoft.com/en-us/azure/virtual-network/service-tags-overview) or URLs.
Notice that since Nexus Shared Service is running on an App Service, the outgoing exceptions are made for the calls coming out of the Web App Subnet.

| Service Tag / Destination | Justification |
| --- | --- |
| AzureActiveDirectory | Authorize the signed in user against Azure Active Directory. |
| AzureContainerRegistry | Pull the Nexus container image, as it is located in Azure Container Registry.  |
| AzureMonitor | Forwards tracing an logs to central location for troubleshooting. |
| pypi.org | Enables Nexus to "proxy" python packages to use inside of workspaces |
