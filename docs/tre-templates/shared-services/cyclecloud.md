# Azure CycleCloud Shared Service
Azure CycleCloud is an enterprise-friendly tool for orchestrating and managing High Performance Computing (HPC) environments on Azure. This shared service deploys a single CycleCloud server, which can be used to by a TRE Administrator to create and manage multiple HPC clusters.

Using the CycleCloud cluster properties the TRE Adminsitrator can choose which virtual network the cluster will be deployed into, and hence the workspace the cluster can be accessed from.

At present there is no self service cluster creation for research teams, however this could be added in the future, and is tracked in this issue <https://github.com/microsoft/AzureTRE/issues/2230> .


## Deployment and Configuration

The CycleCloud shared service template needs registering with the TRE as per <../../tre-admins/registering-templates/> The templates can be found at `templates/shared_services/cyclecloud`.

Prior to deploying the CycleCloud server, the license terms for any Azure VM marketplace images used by CycleCloud must be accepted. This can be done by running the following command while logged into the Azure CLI:

```shell
az vm image terms accept --urn azurecyclecloud:azure-cyclecloud:cyclecloud8:latest
az vm image terms accept --urn almalinux:almalinux-hpc:8_5-hpc:latest
```

Deploy the CycleCloud server using UI or API.

To connect to the CycleCloud server, the TRE Administrator must connect to the CycleCloud server from the administration jumpbox. Use Azure Bastion to connect to the jumpbox a with the username `admin` and the select the password located in your core KeyVault. Connect to the CycleCloud server at the URL: `https://cyclecloud-{TRE_ID}.{LOCATION}.cloudapp.azure.com/`.

- Provide a name for the cyclecloud server instance:
![CycleCloud Step 1](vscode-remote://dev-container%2B5c5c77736c2e6c6f63616c686f73745c5562756e74755c7265706f735c6d6172726f62692d617a7572652d747265/workspaces/marrobi-azure-tre/docs/assets/cyclecloud-1.jpg)

-Review the terms and conditions and hit next.

- Provide your user details, including SSH key
![Enter user detials](vscode-remote://dev-container%2B5c5c77736c2e6c6f63616c686f73745c5562756e74755c7265706f735c6d6172726f62692d617a7572652d747265/workspaces/marrobi-azure-tre/docs/assets/cyclecloud-3.jpg)

- Hit Done, and wait for the add subscription dialog:
![Add Subscription](vscode-remote://dev-container%2B5c5c77736c2e6c6f63616c686f73745c5562756e74755c7265706f735c6d6172726f62692d617a7572652d747265/workspaces/marrobi-azure-tre/docs/assets/cyclecloud-4.jpg)

Select the region your TRE is deployed into, leave the resource group as the default `<Create New Per Cluster>` and select the storage account beginning `stgcc`.

- Hit Save, and then "Back to Clusters"

## Create a Slurm Cluster

- Before you start retrieve the last 4 digits of the workspace ID that you want to deploy the cluster into.

- Select Slurm
![](vscode-remote://dev-container%2B5c5c77736c2e6c6f63616c686f73745c5562756e74755c7265706f735c6d6172726f62692d617a7572652d747265/workspaces/marrobi-azure-tre/docs/assets/cyclecloud-create-cluster.jpg)

- Give the cluster a name - we suggest using the last 4 digits of the workspace ID as part of the name.Click Next.

- Select your required settings. In the **Subnet ID** box, choose the `ServicesSubnet` in the resource gorup and virtual network containing the 4 digit workspace ID. Click Next.

- Configure storage settings and click Next.

- Under advanced settings, under advanced networking - uncheck Return Proxy, and Public Head node. Click Next.

- Under cloud init, paste the below script, with the appropriate values for TRE ID and Region into each of the nodes to ensure the package mirror is used.

```shell
#!/bin/sh
ls /etc/yum.repos.d/*.repo | xargs sed -i 's/mirrorlist/# mirrorlist/g'
ls /etc/yum.repos.d/*.repo | xargs sed -i 's,# baseurl=https://repo.almalinux.org/,baseurl=https://nexus-<tre_id>.<region>.cloudapp.azure.com/repository/almalinux/,g'

yum -y install epel-release
ls /etc/yum.repos.d/*.repo | xargs sed -i 's/metalink/# metalink/g'
ls /etc/yum.repos.d/*.repo | xargs sed -i 's,#baseurl=https://download.fedoraproject.org/,baseurl=https://nexus-<tre_id>.<region>.cloudapp.azure.com/repository/fedoraproject/,g'

yum -y install python3 python3-pip

sudo tee /etc/pip.conf <<'EOF'
[global]
index = https://nexus-<tre_id>.<region>.cloudapp.azure.com/repository/pypi/pypi
index-url = https://nexus-<tre_id>.<region>.cloudapp.azure.com/repository/pypi/simple
trusted-host = https://nexus-<tre_id>.<region>.cloudapp.azure.com
EOF

sudo cat > /etc/yum.repos.d/cyclecloud.repo <<EOF
[cyclecloud]
name=cyclecloud
baseurl=https://nexus-<tre_id>.<region>.cloudapp.azure.com/repository/microsoft-yumrepos/cyclecloud
gpgcheck=1
gpgkey=https://nexus-<tre_id>.<region>.cloudapp.azure.com/repository/microsoft-keys/microsoft.asc
EOF

```

- Under cluster access add a user for workspace access (create a user in advance)

- Start the cluster.
