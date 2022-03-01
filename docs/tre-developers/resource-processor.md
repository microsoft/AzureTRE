# Resource Processor (VMSS)

Resource Processor is the Azure TRE component automating [Porter](https://porter.sh) bundle deployments. It hosts Porter and its dependencies.

## Build and run the container

1. Navigate to `resource_processor/` folder and run `docker build` command:

    ```cmd
    docker build -t resource-processor-vm-porter -f ./vmss_porter/Dockerfile .
    ```

1. Run the image:

    ```cmd
    docker run -it -v /var/run/docker.sock:/var/run/docker.sock --env-file .env resource-processor-vm-porter
    ```

## Local development

To work locally in Visual Studio Code within the Dev Container you can use the `Resource Processor` debug profile to run the app. Before using this, you'll need to perform the below steps:

1. First, run `make setup-local-debugging` to whitelist your local IP against your resources and create the neccesary roles for your signed-in credential to access and create Service Bus messages
2. Copy the `tre.env` file from `./templates/core/tre.env` to `./resource_processor/.env`
3. When running locally, Porter will need a Service Principal instead of Managed Service Identity to be able to authenticate with Azure to deploy resources. You can set this up by running:

```bash
az ad sp create-for-rbac --name ResourceProcessorTesting --role Owner --scopes /subscriptions/{YOUR_SUBSCRIPTION_ID}
```

4. Using the `appId` and `password` values from the above output, create new environment variables called `ARM_CLIENT_ID` and `ARM_CLIENT_SECRET` in the `.env` file you just created in the `./resource_processor` directory.
5. Navigate to the Debug panel then select the `Resource Processor` profile, then hit *Start Debugging*.

Once the above is set up you can simulate receiving messages from Service Bus by going to Service Bus explorer on the portal and using a message payload for `SERVICE_BUS_RESOURCE_REQUEST_QUEUE` as follows:

```json
{"action": "install", "id": "a8911125-50b4-491b-9e7c-ed8ff42220f9", "name": "tre-workspace-base", "version": "0.1.0", "parameters": {"azure_location": "westeurope", "workspace_id": "20f9", "tre_id": "myfavtre", "address_space": "192.168.3.0/24"}}
```

This will trigger receiving of messages, and you can freely debug the code by setting breakpoints as desired.

> If you get a credential error when trying to connect to Service Bus, make sure you've authenticated in the AZ CLI first as it uses your local credentials.

## Porter Azure plugin

Resource Processor uses [Porter Azure plugin](https://github.com/getporter/azure-plugins) to store Porter data in TRE management storage account. The storage container, named `porter`, is created during the bootstrapping phase of TRE deployment. The `/resource_processor/run.sh` script generates a `config.toml` file in Porter home folder to enable the Azure plugin when the image is started.

## Debugging the deployed processor on Azure

See the [debugging and troubleshooting guide](../tre-admins/troubleshooting-guide.md).

## Network requirements

The Resource Processor needs to access the following resources outside the Azure TRE VNET via explicit allowed [Service Tags](https://docs.microsoft.com/en-us/azure/virtual-network/service-tags-overview) or URLs.

| Service Tag | Justification |
| --- | --- |
| AzureActiveDirectory | Authenticate with the User Assigned identity to access Azure Resource Manager and Azure Service Bus. |
| AzureResourceManager | Access the Azure control plane to deploy and manage Azure resources. |
| AzureContainerRegistry | Pull the Resource Processor container image, as it is located in Azure Container Registry.  |
| Storage | The Porter bundles stores state between executions in an Azure Storage Account. |
| AzureKeyVault | The Porter bundles might need to create an Azure Key Vault inside of the Workspace. To verify the creation, before a private link connection is created, Terraform needs to reach Key Vault over public network |

To install Docker, Porter and related packages ([script](/templates/core/terraform/resource_processor/vmss_porter/cloud-config.yaml)) on the Resource Processor, the VM must have access to download from the following URLs:

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

## Challenges

The notable challenges that needed to be solved included Porter automation, namely hosting environment, managing workspace (deployment) states and concurrency.

<!-- markdownlint-disable MD013 -->
Hosting the Porter runner in a container is an expected design idea and appealing due to its cost effectiveness among other things. However, that would create a nested Docker environment, "Docker in Docker". Although this is possible using [Azure CNAB Driver](https://github.com/deislabs/cnab-azure-driver), the solution is less reliable and troubleshooting becomes difficult; due to the environment's ephemeral nature, there is not much in addition to the [Application Insights](https://docs.microsoft.com/azure/azure-monitor/app/app-insights-overview) logs the developer can rely on. In contrast, the developer can always log in to the VM and see what's going on and run tests manually to reproduce bugs.

Porter can keep tap on the installations, but Azure TRE needs a state record that is more tangible. It is instead the responsibility of the API to maintain the state of deployments in configuration store. The state is updated when a user deploys, modifies or deletes workspaces and based on the deployment status messages sent by Resource Processor. All possible states of a workspace or a workspace service are defined by the API in [`resource.py` file](https://github.com/microsoft/AzureTRE/blob/main/api_app/models/domain/resource.py).
<!-- markdownlint-enable MD013 -->
