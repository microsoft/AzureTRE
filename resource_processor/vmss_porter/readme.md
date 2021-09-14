# VMSS Processor

## Build and run Docker container

```cmd
docker build -t resource-processor-vm-porter -f ./vmss_porter/Dockerfile .

docker run -it -v /var/run/docker.sock:/var/run/docker.sock --env-file .env resource-processor-vm-porter
```

## Local development

To work locally checkout the source code and run

``pip install -r requirements.txt``

If you use visual studio code you can set up your launch.json to include the follwing block which will enable launching and debugging.

```json
{
      "name": "VMSS Processor",
      "type": "python",
      "request": "launch",
      "program": "vmss_porter/runner.py",
      "console": "integratedTerminal",
      "cwd": "${workspaceFolder}/resource_processor",
      "env": {
        "PYTHONPATH": ".",
        "AZURE_CLIENT_ID": "",
        "AZURE_CLIENT_SECRET": "",
        "AZURE_TENANT_ID": "",
        "REGISTRY_SERVER": "",
        "TERRAFORM_STATE_CONTAINER_NAME": "",
        "MGMT_RESOURCE_GROUP_NAME": "",
        "MGMT_STORAGE_ACCOUNT_NAME": "",
        "SERVICE_BUS_DEPLOYMENT_STATUS_UPDATE_QUEUE": "deploymentstatus",
        "SERVICE_BUS_RESOURCE_REQUEST_QUEUE": "workspacequeue",
        "SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE": "",
        "ARM_CLIENT_ID": "",
        "ARM_CLIENT_SECRET": "",
        "ARM_TENANT_ID": "",
        "ARM_SUBSCRIPTION_ID": "",
        "ARM_USE_MSI": "false"
      }
}
```

When working locally we use a service principal (SP). This SP needs enough permissions to be able to talk to service bus and to deploy resources into the subscription. That means the service principal needs Owner access to subscription(ARM_SUBSCRIPTION_ID) and also needs **Azure Service Bus Data Sender** and **Azure Service Bus Data Receiver** on the service bus namespace defined above(SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE).

Once the above is setup you can simulate receiving messages from service bus by going to service bus explorer on the portal and using a message payload for SERVICE_BUS_RESOURCE_REQUEST_QUEUE as follows

```json
{"action": "install", "id": "a8911125-50b4-491b-9e7c-ed8ff42220f9", "name": "tre-workspace-base", "version": "0.1.0", "parameters": {"azure_location": "westeurope", "workspace_id": "20f9", "tre_id": "myfavtre", "address_space": "192.168.3.0/24"}}
```

This will trigger receiving of messages and you can freely debug the code by setting breakpoints as desired.

## Debugging deployed processor on Azure

Check the section **Checking the Virtual Machine Scale Set(VMSS) instance running resource processor** in [debugging and troubleshooting guide](../../docs/ops_debugging_troubleshooting.md)

## Network requirements

To be able to run the Resource Processer it needs to acccess the following resource outside the Azure TRE VNET via explicit allowed [Service Tags](https://docs.microsoft.com/en-us/azure/virtual-network/service-tags-overview) or URLs.

| Service Tag | Justification |
| --- | --- |
| AzureActiveDirectory | Authenticate with the User Assigned identity to access Azure Resource Manager and Azure Service Bus. |
| AzureResourceManager | Access the Azure control plane to deploy and manage Azure resources. |
| AzureMonitor | Publish traces and logs to one central place for troubleshooting. |
| AzureContainerRegistry | Pull the Resource Processor container image, as it is located in Azure Container Registry.  |
| Storage | The Porter bundles stores state between executions in an Azure Storage Account. |

To be able to install Docker, Porter and related packages ([script](/templates/core/terraform/resource_processor/vmss_porter/cloud-config.yaml)) on the Resource Processor, the VM must have access to download from the following URLs:

* packages.microsoft.com
* keyserver.ubuntu.com
* api.snapcraft.io
* azure.archive.ubuntu.com
* security.ubuntu.com
* entropy.ubuntu.com
* download.docker.com
* registry-1.docker.io
* auth.docker.io
* registry.terraform.io
* releases.hashicorp.com
