# Nexus Shared Service

Sonatype Nexus (RepoManager) allows users in workspaces to access external software packages securely.

Documentation on Nexus can be found here: [https://help.sonatype.com/repomanager3/](https://help.sonatype.com/repomanager3/).

## Deploy

To deploy set `DEPLOY_NEXUS=true` in `templates/core/.env`.

Nexus will be deployed as part of the main TRE terraform deployment. A configuration script needs to be run once the deployment is done. The script will:

1. Fetch the Nexus generated password from storage account.
2. Reset the default password and set a new one.
3. Store the new password in Key Vault under `nexus-<TRE_ID>-admin-password`
4. Create an anonymous default PyPI proxy repository

## Setup and usage

1. A TRE Administrator can access Nexus though the admin jumpbox provisioned as part of the TRE deployment. The credentials for the jumpbox are located in the KeyVault under `vm-<tre-id>-jumpbox-admin-credentials`
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
| pypi.org | Enables Nexus to "proxy" python packages to use inside of workspaces. |
| repo.anaconda.com | Enables Nexus to "proxy" conda packages to use inside of workspaces. |
| conda.anaconda.org | Enables Nexus to "proxy" additional conda packages to use inside of workspaces such as conda-forge. |
| *.docker.com | Enables Nexus to "proxy" docker repos to use inside of workspaces. |
| *.docker.io | Enables Nexus to "proxy" docker repos to use inside of workspaces. |
| archive.ubuntu.com | Enables Nexus to "proxy" apt packages to use inside of workspaces. |
| security.ubuntu.com | Enables Nexus to "proxy" apt packages to use inside of workspaces. |

## Current Repos

| Name | Type | Source URI | Nexus URI | Usage |
| --- | --- | --- | --- | --- |
| PiPy | PiPy | [https://pypi.org/] | `https://nexus-<TRE_ID>.azurewebsites.net/repository/pypi/` | Allow use of pip commands. |
| Apt PiPy | Apt | [https://pypi.org/] | `https://nexus-<TRE_ID>.azurewebsites.net/repository/apt-pypi/` | Install pip via apt on Linux systems. |
| Conda | conda | [https://repo.anaconda.com/pkgs/main/] | `https://nexus-<TRE_ID>.azurewebsites.net/repository/conda/` | Configure conda to have access to default conda packages. |
| Conda-Forge | conda | [https://conda.anaconda.org/conda-forge/] | `https://nexus-<TRE_ID>.azurewebsites.net/repository/conda-forge/` | Configure conda to have access to conda-forge packages. |
| Docker | apt | [https://download.docker.com/linux/ubuntu/] | `https://nexus-<TRE_ID>.azurewebsites.net/repository/docker/` | Install Docker via apt on Linux systems.|
| Docker GPG | raw | [https://download.docker.com/linux/ubuntu/] | `https://nexus-<TRE_ID>.azurewebsites.net/repository/docker-public-key/` | Provide public key to sign apt source for above Docker apt. |
| Docker Hub | docker | [https://registry-1.docker.io] | `https://nexus-<TRE_ID>.azurewebsites.net/repository/docker-hub/` | Provide docker access to public images repo. |
| Ubuntu Packages | apt | [http://archive.ubuntu.com/ubuntu/] | `https://nexus-<TRE_ID>.azurewebsites.net/repository/ubuntu/` | Provide access to Ubuntu apt packages on Ubuntu systems. |
| Ubuntu Security Packages | apt | [http://security.ubuntu.com/ubuntu/] | `https://nexus-<TRE_ID>.azurewebsites.net/repository/ubuntu-security/` | Provide access to Ubuntu Security apt packages on Ubuntu systems. |
