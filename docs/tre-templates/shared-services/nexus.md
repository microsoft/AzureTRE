# Nexus Shared Service

Sonatype Nexus (RepoManager) allows users in workspaces to access external software packages securely.

Documentation on Nexus can be found here: [https://help.sonatype.com/repomanager3/](https://help.sonatype.com/repomanager3/).

## Deploy

!!! caution
    Before deploying the Nexus service, you will need workspaces of version `0.3.2` or above due to a dependency on a DNS zone link for the workspace(s) to connect to the Nexus VM.

Before deploying the Nexus shared service, you need to make sure that it will have access to a certificate to configure serving secure proxies. By default, the Nexus service will serve proxies from `https://nexus-{TRE_ID}.{LOCATION}.cloudapp.azure.com/`, and thus it requires a certificate that validates ownership of this domain to use for SSL.

You can use the Certs Shared Service to set one up by following these steps:

1. Run the below command in your terminal to build, publish and register the certs bundle:

  ```cmd
  make shared_service_bundle BUNDLE=certs
  ```

2. Navigate to the TRE UI, click on Shared Services in the navigation menu and click *Create new*.

3. Select the Certs template, then fill in the required details. *Domain prefix* should be set to `nexus` and *Cert name* should be `nexus-ssl`.

!!! caution
    If you have Key Vault Purge Protection enabled and are re-deploying your environment using the same `cert_name`, you may encounter this: `Status=409 Code=\"Conflict\" Message=\"Certificate nexus-ssl is currently in a deleted but recoverable state`. You need to either manually recover the certificate or purge it before redeploying.

Once deployed, the certs service will use Let's Encrypt to generate a certificate for the specified domain prefix followed by `-{TRE_ID}.{LOCATION}.cloudapp.azure.com`, so in our case, having entered `nexus`, this will be `nexus-{TRE_ID}.{LOCATION}.cloudapp.azure.com`, which will be the public domain for our Nexus service.

You can verify whether this has been successful by navigating to your core Key Vault (`kv-{TRE_ID}`) and looking for a certificate called `nexus-ssl` (or whatever you called it).

After verifying the certificate has been generated, you can deploy Nexus:

1. Run the below command in your terminal to build, publish and register the Nexus shared service bundle:

  ```cmd
  make shared_service_bundle BUNDLE=sonatype-nexus-vm
  ```

1. Navigate back to the TRE UI, and click *Create new* again within the Shared Services page.

1. Select the Nexus template, then fill in the required details. The *SSL certificate name* should default to `nexus-ssl`, so there's no need to change it unless you gave it a different name in the previous step.

This will deploy the infrastructure required for Nexus, then start the service and configure it with the repository configurations located in the `./templates/shared_services/sonatype-nexus-vm/scripts/nexus_repos_config` folder. It will also set up HTTPS using the certificate you generated in the previous section, so proxies can be served at `https://nexus-{TRE_ID}.{LOCATION}.cloudapp.azure.com`.

## Setup and usage

1. A TRE Administrator can access Nexus though the admin jumpbox provisioned as part of the TRE deployment. The username is `adminuser` and the password is located in the Key Vault under `vm-<tre-id>-jumpbox-password`
2. A researcher can access Nexus from within the workspace by using the internal Nexus URL of `https://nexus-{TRE_ID}.{LOCATION}.cloudapp.azure.com`
3. To fetch Python packages from the PyPI proxy, a researcher can use `pip install` while specifying the proxy server:

    ```bash
    pip install packagename --index-url https://nexus-{TRE_ID}.{LOCATION}.cloudapp.azure.com/repository/apt-pypi/simple
    ```

!!! info
    In the built-in Linux and Windows Guacamole VM bundles, PyPI and several other package managers are already configured to use the Nexus proxy by default, so manually specifying in the install commands isn't necessary.

## Network requirements

Nexus Shared Service requires access to resources outside of the Azure TRE VNET. These are set as part of the firewall provisioning pipeline via explicit allow on [Service Tags](https://docs.microsoft.com/en-us/azure/virtual-network/service-tags-overview) or URLs.

| Service Tag / Destination | Justification |
| --- | --- |
| AzureActiveDirectory | Authorize the signed in user against Microsoft Entra ID. |
| AzureContainerRegistry | Pull the Nexus container image, as it is located in Azure Container Registry.  |
| pypi.org, *.pypi.org | Enables Nexus to "proxy" python packages to use inside of workspaces. |
| repo.anaconda.com | Enables Nexus to "proxy" conda packages to use inside of workspaces. |
| conda.anaconda.org | Enables Nexus to "proxy" additional conda packages to use inside of workspaces such as conda-forge. |
| *.docker.com | Enables Nexus to "proxy" docker repos to use inside of workspaces. |
| *.docker.io | Enables Nexus to "proxy" docker repos to use inside of workspaces. |
| archive.ubuntu.com | Enables Nexus to "proxy" apt packages to use inside of workspaces. |
| security.ubuntu.com | Enables Nexus to "proxy" apt packages to use inside of workspaces. |

## Current Repos

| Name | Type | Source URI | Nexus URI | Usage |
| --- | --- | --- | --- | --- |
| PyPI | PyPI | [https://pypi.org/] | `https://nexus-{TRE_ID}.{LOCATION}.cloudapp.azure.com/repository/pypi/` | Allow use of pip commands. |
| Conda | conda | [https://repo.anaconda.com/pkgs] | `https://nexus-{TRE_ID}.{LOCATION}.cloudapp.azure.com/repository/conda-repo/` | Configure conda to have access to default conda packages. |
| Conda Mirror | conda | [https://conda.anaconda.org] | `https://nexus-{TRE_ID}.{LOCATION}.cloudapp.azure.com/repository/conda-mirror/` | Configure conda to have access to conda mirror packages. |
| Docker | apt | [https://download.docker.com/linux/ubuntu/] | `https://nexus-{TRE_ID}.{LOCATION}.cloudapp.azure.com/repository/docker/` | Install Docker via apt on Linux systems. |
| Docker GPG | raw | [https://download.docker.com/linux/ubuntu/] | `https://nexus-{TRE_ID}.{LOCATION}.cloudapp.azure.com/repository/docker-public-key/` | Provide public key to sign apt source for above Docker apt. |
| Docker Hub | docker | [https://registry-1.docker.io] | `https://nexus-{TRE_ID}.{LOCATION}.cloudapp.azure.com/repository/docker-hub/` | Provide docker access to public images repo. |
| Ubuntu Packages | apt | [http://archive.ubuntu.com/ubuntu/] | `https://nexus-{TRE_ID}.{LOCATION}.cloudapp.azure.com/repository/ubuntu/` | Provide access to Ubuntu apt packages on Ubuntu systems. |
| Ubuntu Security Packages | apt | [http://security.ubuntu.com/ubuntu/] | `https://nexus-{TRE_ID}.{LOCATION}.cloudapp.azure.com/repository/ubuntu-security/` | Provide access to Ubuntu Security apt packages on Ubuntu systems. |
| Almalinux | yum | [https://repo.almalinux.org] | `https://nexus-{TRE_ID}.{LOCATION}.cloudapp.azure.com/repository/almalinux` | Install Almalinux packages |
| R-Proxy | r | [https://cran.r-project.org/] | `https://nexus-{TRE_ID}.{LOCATION}.cloudapp.azure.com/repository/r-proxy` | Provide access to CRAN packages for R |
| R-Studio Download | raw | [https://download1.rstudio.org] | `https://nexus-{TRE_ID}.{LOCATION}.cloudapp.azure.com/repository/r-studio-download` | Provide access to download R Studio |
| Fedora Project | yum | [https://download-ib01.fedoraproject.org] | `https://nexus-{TRE_ID}.{LOCATION}.cloudapp.azure.com/repository/fedoraproject` | Install Fedora Project Linux packages |
| Microsoft Apt | apt | [https://packages.microsoft.com] | `https://nexus-{TRE_ID}.{LOCATION}.cloudapp.azure.com/repository/microsoft-apt` | Provide access to Microsoft Apt packages |
| Microsoft Keys | raw | [https://packages.microsoft.com/keys/] | `https://nexus-{TRE_ID}.{LOCATION}.cloudapp.azure.com/repository/microsoft-keys` | Provide access to Microsoft keys |
| Microsoft Yum | yum | [https://packages.microsoft.com/yumrepos] | `https://nexus-{TRE_ID}.{LOCATION}.cloudapp.azure.com/repository/microsoft-yum` | Provide access to Microsoft Yum packages |
| Microsoft Download | raw | [https://download.microsoft.com/download] | `https://nexus-{TRE_ID}.{LOCATION}.cloudapp.azure.com/repository/microsoft-download` | Provide access to Microsoft Downloads |
| VS Code Extensions | raw | [https://marketplace.visualstudio.com/_apis/public/gallery/publishers/] | `https://nexus-{TRE_ID}.{LOCATION}.cloudapp.azure.com/repository/vscode-extensions/` | Provide access to VS Code extensions |

### Migrate from an existing V1 Nexus service (hosted on App Service)

If you still have an existing Nexus installation based on App Service (from the original V1 bundle), you can migrate to the VM-based Nexus service by following these steps:

1. Install the new Nexus service alongside your old installation using the steps from earlier in this document.

1. Identify any existing Guacamole user resources that are using the old proxy URL (`https://nexus-{TRE_ID}.azurewebsites.net/`). These will be any VMs with bundle versions < `0.3.2` that haven't been manually updated.

1. These will need to be either **re-deployed** with the new template versions `0.3.2` or later and specifying an additional template parameter `"nexus_version"` with the value of `"V2"`, or manually have their proxy URLs updated by remoting into the VMs and updating the various configuration files of required package managers with the new URL (`https://nexus-{TRE_ID}.{LOCATION}.cloudapp.azure.com/`).

   1. For example, pip will need the `index`, `index-url` and `trusted-host` values in the global `pip.conf` file to be modified to use the new URL.

2. Once you've confirmed there are no dependencies on the old Nexus shared service, you can delete it using the API or UI.

## Renewing certificates for Nexus

The Nexus service checks Key Vault regularly for the latest certificate matching the name you passed on deploy (`nexus-ssl` by default).

When approaching expiry, you can either provide an updated certificate into the TRE core KeyVault (with the name you specified when installing Nexus) if you brought your own, or if you used the certs shared service to generate one, just call the `renew` custom action on that service. This will generate a new certificate and persist it to the Key Vault, replacing the expired one.

## Updating to v3.0.0
The newest version of Nexus is a significant update for the service.
As a result, a new installation of Nexus will be necessary.

We are currently in the process of developing an upgrade path for upcoming releases.

## Using Docker Hub
When using Docker with a VM, the image URL should be constructed as follows: {NEXUS_URL}:{port}/docker-image

```bash
sudo docker pull {NEXUS_URL}:8083/hello-world
```

the default port out of the box is 8083

Nexus will also need "Anonymous Access" set to "Enable". This can be done by logging into the Nexus Portal with the Admin user and following the prompts.

## Using the VS Code Extensions

To fetch and install VS Code extensions, use the following commands:

```bash
curl -o {publisher}-{extension}-{version}.vsix https://nexus-{TRE_ID}.{LOCATION}.cloudapp.azure.com/repository/vscode-extensions/{publisher}/vsextensions/{extension}/{version}/vspackage

code --install-extension {publisher}-{extension}-{version}.vsix
```

The extensions which are  available to users can be restricted by configuring content selectors using the package `path` via the SonatypeNexus RM web interface.

If extensions want to be intalled in bulk, a script such as the following can be used:

```bash
#!/bin/bash

# Function to display usage
usage() {
    echo "Usage: $0 -t TRE_ID -l LOCATION [--install]"
    exit 1
}

# Parse command line arguments
INSTALL=false
while [[ "$#" -gt 0 ]]; do
    case $1 in
        -t|--tre-id) TRE_ID="$2"; shift ;;
        -l|--location) LOCATION="$2"; shift ;;
        --install) INSTALL=true ;;
        *) usage ;;
    esac
    shift
done

# Check if TRE_ID and LOCATION are provided
if [ -z "$TRE_ID" ] || [ -z "$LOCATION" ]; then
    usage
fi

# Define the list of extensions
extensions=(
    "ms-python.debugpy@2024.14.0"
    "ms-python.python@2024.22.0"
    "ms-python.vscode-pylance@2024.12.1"
    "ms-toolsai.datawrangler@1.14.0"
    "ms-toolsai.jupyter@2024.10.0"
    "ms-toolsai.jupyter-keymap@1.1.2"
    "ms-toolsai.jupyter-renderers@1.0.21"
    "ms-toolsai.vscode-jupyter-cell-tags@0.1.9"
    "ms-toolsai.vscode-jupyter-slideshow@0.1.6"
)

# Define the base URL
base_url="https://nexus-${TRE_ID}.${LOCATION}.cloudapp.azure.com/repository/vscode-extensions"

# Loop through each extension and download it
for ext in "${extensions[@]}"; do
    IFS='@' read -r publisher_extension version <<< "$ext"
    IFS='.' read -r publisher extension <<< "$publisher_extension"
    vsix_file="${publisher}-${extension}-${version}.vsix"
    curl -o "$vsix_file" "${base_url}/${publisher}/vsextensions/${extension}/${version}/vspackage"
    
    # Install the extension if --install flag is set
    if [ "$INSTALL" = true ]; then
        code --install-extension "$vsix_file"
    fi
done
```
