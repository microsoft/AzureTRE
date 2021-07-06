# Processor function

The Resource Processor is an Azure Function...

## Prerequisites

Tools:

* [Python 3.x](https://www.python.org/downloads/)
* [Azure Function Core Tools](https://docs.microsoft.com/azure/azure-functions/functions-run-local?tabs=windows%2Ccsharp%2Cbash#install-the-azure-functions-core-tools) - For testing locally

Resources:

* [Application Insights](https://docs.microsoft.com/azure/azure-monitor/app/app-insights-overview) - Not required for testing locally
* [Azure Container Registry](https://docs.microsoft.com/azure/container-registry/) with a workspace image (bundle) to deploy
  * See [Authoring workspaces](../docs/authoring-workspaces.md)
* [Azure Service Bus](https://docs.microsoft.com/azure/service-bus-messaging/) with two queues:
  * Resource request queue for messages triggering the function
  * Deployment status update queue for messages function sends about the progress of the deployment

## Configuration

| Environment variable name | Description | Required for local testing |
| ------------------------- | ----------- | -------------------------- |
| `APPINSIGHTS_INSTRUMENTATIONKEY` | Application Insights instrumentation key. | No |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | Application Insights connection string. | No |
| `RESOURCE_GROUP_NAME` |  |  |
| `VNET_NAME` |  |  |
| `ACI_SUBNET` |  |  |
| `CNAB_AZURE_STATE_PATH` |  |  |
| `CNAB_AZURE_STATE_FILESHARE` |  |  |
| `CNAB_AZURE_SUBSCRIPTION_ID` |  |  |
| `CNAB_AZURE_USER_MSI_RESOURCE_ID` |  |  |
| `CNAB_AZURE_VERBOSE` |  |  |
| `CNAB_AZURE_PROPAGATE_CREDENTIALS` |  |  |
| `CNAB_AZURE_MSI_TYPE` |  |  |
| `CNAB_AZURE_STATE_STORAGE_ACCOUNT_NAME` |  |  |
| `SEC_CNAB_AZURE_STATE_STORAGE_ACCOUNT_KEY` |  |  |
| `SEC_CNAB_AZURE_REGISTRY_USERNAME` |  |  |
| `SEC_CNAB_AZURE_REGISTRY_PASSWORD` |  |  |
| `SEC_ARM_TENANT_ID` |  |  |
| `SEC_ARM_SUBSCRIPTION_ID` |  |  |
| `SEC_ARM_CLIENT_ID` |  |  |
| `SEC_ARM_CLIENT_SECRET` |  |  |
| `MANAGED_IDENTITY_CLIENT_ID` |  |  |
| `SERVICE_BUS_CONNECTION_STRING` | The connection string of an Azure Service Bus resource instance. | Yes |
| `SERVICE_BUS_RESOURCE_REQUEST_QUEUE` | The name of the Service Bus queue for resource requests that trigger the function. | Yes |
| `SERVICE_BUS_DEPLOYMENT_STATUS_UPDATE_QUEUE` | The name of the Service Bus queue for deployment status update messages sent by the function. | Yes |
| `REGISTRY_SERVER` | The URL of the container registry e.g., `https://<Container registry name>.azurecr.io` | Yes |
| `WORKSPACES_PATH` | The path of the repository containing the workspace images (bundles). The value must start and end with a forward slash as it is concatenated with the values of `REGISTRY SERVER` and the name of the bundle to act upon. Example: `/microsoft/azuretre/workspaces/` | Yes |
| `CNAB_IMAGE` | The full URL of the CNAB container image used for running Porter e.g., `https://<Container registry name>.azurecr.io/microsoft/azuretre/cnab-aci:v1.0.0` | Yes |
| `param_tfstate_resource_group_name` |  |  |
| `param_tfstate_storage_account_name` |  |  |
| `param_tfstate_container_name` |  |  |

When deploying the processor function using infrastructure as code (IaC), the environment variables are set in [`function.tf`](../templates/core/terraform/processor_function/function.tf) Terraform file.

## Running the function locally

1. Install the required Python libraries (`requirements.txt` file located in `/processor_function/` folder):

    ```cmd
    pip install -r requirements.txt
    ```

1. Set the environment variables

    * When using `.env` file in Unix shell (e.g., Bash), the utility script [`load_env.sh`](../devops/scripts/load_env.sh) can be used:

        ```bash
        $ . ../devops/scripts/load_env.sh .env
        ```

        > Check with the `env` command that the environment variables were effectively set e.g.,
        >
        > ```bash
        > env | grep RESOURCE_GROUP_NAME
        > ```

1. Start the function using either of the two following ways:

    * Using Azure Function Core Tools in command line:

        ```cmd
        func start
        ```

    * **OR** [run the function locally in Visual Studio Code](https://docs.microsoft.com/azure/azure-functions/create-first-function-vs-code-python#run-the-function-locally)

1. Trigger the function by sending a Service Bus message (see below)

### Triggering the function

A small test utility written in Python is available in folder `/processor_function/test_tools/service_bus_message_sender/`. It attempts to send the content in [`createWorkspaceRequestData.json`](./test_tools/service_bus_message_sender/createWorkspaceRequestData.json) to the resource request queue.

The sender depends on two of the same Service Bus environment variables as the function itself:

* `SERVICE_BUS_CONNECTION_STRING`
* `SERVICE_BUS_RESOURCE_REQUEST_QUEUE`

Make sure the content in the `createWorkspaceRequestData.json` file and the Service Bus environment variables are correct for your test scenario. Then execute the script in the `service_bus_message_sender` folder:

```cmd
py send_message_to_servicebus.py
```

The output of the script will indicate whether the message was sent successfully or not. Upon a successful sending of the message, the function will pick up the message and execute.

## Unit tests

The unit tests are located in folder `/processor_function/tests/`. To execute the unit tests run command `pytest` in `/processor_function/` folder.
