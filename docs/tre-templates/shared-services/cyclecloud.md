# Azure CycleCloud Shared Service
Azure CycleCloud is an enterprise-friendly tool for orchestrating and managing High Performance Computing (HPC) environments on Azure. This shared service deploys a single CycleCloud server, which can be used to by a TRE Administrator to create and manage multiple HPC clusters.

Using the CycleCloud cluster properties the TRE Adminsitrator can choose which virtual network the cluster will be deployed into, and hence the workspace the cluster can be accessed from.

At present there is no self service cluster creation for research teams, however this could be added in the future, and is tracked in this issue <https://github.com/microsoft/AzureTRE/issues/2230> .


## Deployment and Configuration

The CycleCloud shared service template needs registering with the TRE as per **add link to registering templates** The templates can be found at `templates/shared_services/cyclecloud`.

Prior to deploying the CycleCloud server, the licence terms for any Azure VM marketplace images used by CycleCloud must be accepted. This can be done by running the following command while logged into the Azure CLI:

```shell
az vm image terms accept --urn azurecyclecloud:azure-cyclecloud:cyclecloud8:latest
az vm image terms accept --urn almalinux:almalinux-hpc:8_5-hpc:latest
```


To connect to 
```shell
#!/bin/sh
ls /etc/yum.repos.d/*.repo | xargs sed -i 's/mirrorlist/# mirrorlist/g'
ls /etc/yum.repos.d/*.repo | xargs sed -i 's,# baseurl=https://repo.almalinux.org/,baseurl=https://nexus-mrtredemo1.westeurope.cloudapp.azure.com/repository/almalinux/,g'

yum -y install epel-release
ls /etc/yum.repos.d/*.repo | xargs sed -i 's/metalink/# metalink/g'
ls /etc/yum.repos.d/*.repo | xargs sed -i 's,#baseurl=https://download.fedoraproject.org/,baseurl=https://nexus-mrtredemo1.westeurope.cloudapp.azure.com/repository/fedoraproject/,g'

yum -y install python3 python3-pip

sudo tee /etc/pip.conf <<'EOF'
[global]
index = https://nexus-mrtredemo1.westeurope.cloudapp.azure.com/repository/pypi/pypi
index-url = https://nexus-mrtredemo1.westeurope.cloudapp.azure.com/repository/pypi/simple
trusted-host = https://nexus-mrtredemo1.westeurope.cloudapp.azure.com
EOF

sudo cat > /etc/yum.repos.d/cyclecloud.repo <<EOF
[cyclecloud]
name=cyclecloud
baseurl=https://nexus-mrtredemo1.westeurope.cloudapp.azure.com/repository/microsoft-yumrepos/cyclecloud
gpgcheck=1
gpgkey=https://nexus-mrtredemo1.westeurope.cloudapp.azure.com/repository/microsoft-keys/microsoft.asc
EOF

```
