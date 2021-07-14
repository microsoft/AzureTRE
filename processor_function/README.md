# Resource Processor Function

<!-- markdownlint-disable-next-line MD013 -->
Resource Processor Function (sometimes referred to as the deployment processor) uses [Azure Container Instances (ACI)](https://docs.microsoft.com/en-us/azure/container-instances/) together with the [CNAB container image](../CNAB_container/Dockerfile), based on [Azure CNAB Driver](https://github.com/deislabs/cnab-azure-driver), to execute workspace and workspace service deployments. The workspace and workspace service packages are implemented as [Porter](https://porter.sh/) bundles.

<!-- markdownlint-disable-next-line MD013 -->
The processor function waits for Service Bus messages, sent by [Management API](../management_api_app/README.md), in the resource request queue containing the bundle details and the action to execute, prepares the environment for the execution in the ACI and follows through the deployment process. The deployment status is reported back to Management API using Service Bus messages but with in a deployment status update queue.

*Table of contents:*

* [Prerequisites](#prerequisites)
  * [Tools](#tools)
  * [Azure resources](#azure-resources)
* [Configuration](#configuration)
  * [General](#general)
  * [Azure CNAB Driver](#azure-cnab-driver)
  * [Service Bus](#service-bus)
  * [Required by workspace and service templates](#required-by-workspace-and-service-templates)
* [Running the function locally](#running-the-function-locally)
  * [Triggering the function](#triggering-the-function)
  * [Troubleshooting](#troubleshooting)
* [Observability](#observability)
* [Unit tests](#unit-tests)

## Prerequisites

### Tools

* [Python 3.8.x](https://www.python.org/downloads/)
* [Azure Function Core Tools](https://docs.microsoft.com/azure/azure-functions/functions-run-local?tabs=windows%2Ccsharp%2Cbash#install-the-azure-functions-core-tools) - For testing locally
  * [The package source for Linux](https://www.npmjs.com/package/azure-functions-core-tools#linux) varies depending the version of the Linux distribution. Use command "`lsb_release -a`" to check your version.

### Azure resources

* [Application Insights](https://docs.microsoft.com/azure/azure-monitor/app/app-insights-overview) - Not required for testing locally
* [Azure Container Instances](https://docs.microsoft.com/azure/container-instances/)
* [Azure Container Registry](https://docs.microsoft.com/azure/container-registry/) with:
  * The [CNAB container image](../CNAB_container/Dockerfile)
  * A workspace image (bundle) to deploy (see [Authoring workspaces](../docs/authoring-workspace-templates.md))
* [Azure Service Bus](https://docs.microsoft.com/azure/service-bus-messaging/) with two queues:
  * Resource request queue for messages triggering the function
  * Deployment status update queue for messages function sends about the progress of the deployment

## Configuration

When deploying the processor function using infrastructure as code (IaC), the environment variables for this function are set in [`function.tf`](../templates/core/terraform/processor_function/function.tf) Terraform file.

### General

| Environment variable name | Description |
| ------------------------- | ----------- |
| `AzureWebJobsStorage` | For testing locally. See [App settings reference for Azure Functions](https://docs.microsoft.com/en-us/azure/azure-functions/functions-app-settings#azurewebjobsstorage). |
| `APPINSIGHTS_INSTRUMENTATIONKEY` | Application Insights instrumentation key. |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | Application Insights connection string. |
| `RESOURCE_GROUP_NAME` | The name of the resource group containing the ACI. |
| `VNET_NAME` | The name of the Azure TRE (core) VNet. |
| `ACI_SUBNET` | The subnet for the ACI. |
| `REGISTRY_SERVER` | The URL of the container registry e.g., `https://<Container registry name>.azurecr.io` |
| `WORKSPACES_PATH` | The path of the repository containing the workspace images (bundles). The value must start and end with a forward slash as it is concatenated with the values of `REGISTRY SERVER` and the name of the bundle to act upon. Example: `/microsoft/azuretre/workspaces/`. If the repositories do not have an extended path, leave the value empty. |
| `CNAB_IMAGE` | The full URL of the CNAB container image used for running Porter e.g., `https://<Container registry name>.azurecr.io/microsoft/azuretre/cnab-aci:v1.0.0` |

### Azure CNAB Driver

See [Azure CNAB Driver environment variables](https://github.com/deislabs/cnab-azure-driver#environment-variables) for the description of the following environment variables.

| Environment variable name | Note |
| ------------------------- | ---- |
| `CNAB_AZURE_VERBOSE` | |
| `CNAB_AZURE_SUBSCRIPTION_ID` | |
| `CNAB_AZURE_USER_MSI_RESOURCE_ID` | |
| `CNAB_AZURE_MSI_TYPE` | |
| `CNAB_AZURE_PROPAGATE_CREDENTIALS` | |
| `CNAB_AZURE_STATE_PATH` | |
| `CNAB_AZURE_STATE_FILESHARE` | |
| `CNAB_AZURE_STATE_STORAGE_ACCOUNT_NAME` | |
| `SEC_CNAB_AZURE_STATE_STORAGE_ACCOUNT_KEY` | The `SEC_` prefix is dropped when setting up the ACI and it the environment variable name is without it in [Azure CNAB Driver documentation](https://github.com/deislabs/cnab-azure-driver#environment-variables). |
| `SEC_CNAB_AZURE_REGISTRY_USERNAME` |  The `SEC_` prefix is dropped when setting up the ACI and it the environment variable name is without it in [Azure CNAB Driver documentation](https://github.com/deislabs/cnab-azure-driver#environment-variables). |
| `SEC_CNAB_AZURE_REGISTRY_PASSWORD` |  The `SEC_` prefix is dropped when setting up the ACI and it the environment variable name is without it in [Azure CNAB Driver documentation](https://github.com/deislabs/cnab-azure-driver#environment-variables). |
| `MANAGED_IDENTITY_CLIENT_ID` | The application (client) ID associated with the user assigned, managed identity for ACI. The managed identity here is the same referred to by `CNAB_AZURE_USER_MSI_RESOURCE_ID` and `CNAB_AZURE_MSI_TYPE`.  |

### Service Bus

| Environment variable name | Description |
| ------------------------- | ----------- |
| `SERVICE_BUS_CONNECTION_STRING` | The connection string of an Azure Service Bus resource instance. |
| `SERVICE_BUS_RESOURCE_REQUEST_QUEUE` | The name of the Service Bus queue for resource requests that trigger the function. |
| `SERVICE_BUS_DEPLOYMENT_STATUS_UPDATE_QUEUE` | The name of the Service Bus queue for deployment status update messages sent by the function. |

### Required by workspace and service templates

| Environment variable name | Description |
| ------------------------- | ----------- |
| `SEC_ARM_TENANT_ID` | The tenant ID of a service principal with privileges to provision workspace resources. See [Authoring workspaces - Credentials](../docs/authoring-workspace-templates.md#credentials). |
| `SEC_ARM_SUBSCRIPTION_ID` | The subscription ID of a service principal with privileges to provision workspace resources. See [Authoring workspaces - Credentials](../docs/authoring-workspace-templates.md#credentials). |
| `SEC_ARM_CLIENT_ID` | The application (client) ID of a service principal with privileges to provision workspace resources. See [Authoring workspaces - Credentials](../docs/authoring-workspace-templates.md#credentials). |
| `SEC_ARM_CLIENT_SECRET` | The application password (client secret) of a service principal with privileges to provision workspace resources. See [Authoring workspaces - Credentials](../docs/authoring-workspace-templates.md#credentials). |
| `param_tfstate_resource_group_name` | The name of the resource group containing the Terraform state store for the workspace/service deployment. |
| `param_tfstate_storage_account_name` | The name of the storage account containing the Terraform state store for the workspace/service deployment. |
| `param_tfstate_container_name` | The name of the container for the Terraform state store for the workspace/service deployment. |

See [Authoring Workspace Templates](../docs/authoring-workspace-templates.md) for more information.

## Running the function locally

1. Install the required Python libraries (`requirements.txt` file located in `/processor_function/` folder):

    ```cmd
    pip install -r requirements.txt
    ```

1. Set the environment variables

    * Use [`.env.sample`](./.env.sample) in `/processor_function/` folder as the basis; copy the file and rename it "`.env`" and fill the values
    * In Unix shell (e.g., Bash), use the utility script [`load_env.sh`](../devops/scripts/load_env.sh) to load the variables:

        ```bash
        . ../devops/scripts/load_env.sh .env
        ```

        > Check with the `env` command that the environment variables were effectively set e.g.,
        >
        > ```bash
        > env | grep RESOURCE_GROUP_NAME
        > ```

    * In PowerShell, use the [`Set-Env.ps1`](../devops/scripts/Set-Env.ps1) script:

        ```ps1
        ..\devops\scripts\Set-Env.ps1 .\.env
        ```

1. Start the function using either of the two following ways:

    * Using Azure Function Core Tools in command line:

        ```cmd
        func start --python
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

The script will also generate and output a correlation ID that is injected into the Service Bus message. The ID can be used to query the Application Insights logs of the operation. For more information see [Observability](#observability).

### Troubleshooting

#### ModuleNotFoundError: No module named 'shared'

Error message:

```plaintext
[...] System.Private.CoreLib: Exception while executing function: Functions.createNewWorkspace. System.Private.CoreLib: Result: Failure
Exception: ModuleNotFoundError: No module named 'shared'
...
```

Solution: Set `PYTHOHPATH` environment variable to point to the root of the `processor_function` folder. When running in the root folder:

* Bash:

    ```bash
    export PYTHONPATH=.
    ```

* PowerShell

    ```ps1
    $Env:PYTHONPATH="."
    ```

## Observability

<!-- markdownlint-disable-next-line MD013 -->
When the function is triggered by a Service Bus message, the correlation ID in the message is used to create a new Python logging adapter (see [main `__init__.py`](./createNewWorkspace/__init__.py) and [`logging.py`](./shared/logging.py)). The adapter is then passed on to [the `CNABBuilder` class](./shared/cnab_builder.py) instance and when used, each log entry sent to Application Insights will have an `operation_Id` field matching the correlation ID. Using the ID, the logs for a specific deployment operation can be easily collected with a query e.g.:

```plaintext
traces
| where operation_Id == "3aee3870-3836-494d-8abf-620207240211"
```

## Unit tests

The unit tests are located in folder `/processor_function/tests_pf/`. To execute the unit tests run command `pytest` in `/processor_function/` folder.
