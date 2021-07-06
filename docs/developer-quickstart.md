# Developer Setup

- [Prerequisite Azure resource](#prerequisite-azure-resource)
- [Running the Management API](#running-the-management-api)
- [Running the Resource Processor function](#running-the-resource-processor-function)
- [(Optional) Install pre-commit hooks](#optional-install-pre-commit-hooks)
- [API Endpoints](#api-endpoints)
- [Management API Project Structure](#management-api-project-structure)

> This guide assumes usage of Bash for development.

## Prerequisite Azure resource

To develop locally you required the following Azure services:

- Azure CosmosDB (SQL)
- Azure Service Bus
- Service Principal for the API to access Azure services such as Azure Service Bus
- AAD applications (for API and Swagger UI) registered with the Microsoft Identity Platform

The solution consists of two services:

- Management API ([src](/management_api_app/))
- Resource Processor ([src](/processor_function/))

Execute the following steps to set up a development environment.

1. Login and select the Azure subscription you wish to deploy to

    ```cmd
    az login
    az account list
    az account set -s <subscription_name_or_id>
    ```

1. Create Azure Service Bus

    ```bash
    RESOURCE_GROUP=<resource_group_name>
    LOCATION=westeurope
    SERVICE_BUS_NAMESPACE=<service_bus_namespace_name>
    SERVICE_BUS_RESOURCE_REQUEST_QUEUE=workspacequeue
    SERVICE_BUS_DEPLOYMENT_STATUS_UPDATE_QUEUE=deploymentstatus

    az servicebus namespace create --resource-group $RESOURCE_GROUP --name $SERVICE_BUS_NAMESPACE --location $LOCATION
    az servicebus queue create --resource-group $RESOURCE_GROUP --namespace-name $SERVICE_BUS_NAMESPACE --name $SERVICE_BUS_RESOURCE_REQUEST_QUEUE
    az servicebus queue create --resource-group $RESOURCE_GROUP --namespace-name $SERVICE_BUS_NAMESPACE --name $SERVICE_BUS_DEPLOYMENT_STATUS_UPDATE_QUEUE
    ```

1. Create Cosmos DB

    You have two options - create a Cosmos DB in Azure or run the Cosmos DB emulator locally.

    Create an [Azure Cosmos DB](https://docs.microsoft.com/en-us/azure/cosmos-db/create-cosmosdb-resources-portal):

    ```bash
    COSMOS_NAME=<cosmos_name>
    COSMOS_DB_NAME=<database_name>

    az cosmosdb create -n $COSMOS_NAME -g $RESSOURCE_GROUP --locations regionName=$LOCATION
    az cosmosdb sql database create -a $COSMOS_NAME -g $RESSOURCE_GROUP -n $COSMOS_DB_NAME
    ```

    Or [install the Cosmos DB Emulator](https://docs.microsoft.com/en-us/azure/cosmos-db/local-emulator?tabs=cli%2Cssl-netstd21).

1. [Create a Service Principal](https://docs.microsoft.com/en-us/cli/azure/create-an-azure-service-principal-azure-cli) and assign it permissions

    ```bash
    # Save the AppId, Password, and Tenant as you will need them to configure the services (environment variables)
    az ad sp create-for-rbac --name ServicePrincipalName

    SERVICE_PRINCIPAL_ID=<the AppId of the Service Principal>
    SUBSCRIPTION_ID=$(az account show --query id --output tsv)

    az role assignment create \
        --role "Azure Service Bus Data Sender" \
        --assignee $SERVICE_PRINCIPAL_ID \
        --scope /subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESSOURCE_GROUP/providers/Microsoft.ServiceBus/namespaces/$SERVICE_BUS_NAMESPACE

    az role assignment create \
        --role "Azure Service Bus Data Receiver" \
        --assignee $SERVICE_PRINCIPAL_ID \
        --scope /subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESSOURCE_GROUP/providers/Microsoft.ServiceBus/namespaces/$SERVICE_BUS_NAMESPACE
    ```

    > Keep in mind that Azure role assignments may take up to five minutes to propagate.

1. Register AAD applications with the Microsoft Identity Platform

   > NOTE: this requires domain admin privileges. You may wish to set up a separate Azure AD tenant for this

   Follow the [Microsoft Docs Quickstart](https://docs.microsoft.com/en-us/azure/active-directory/develop/quickstart-register-app) or run the [AAD App Reg script](../scripts/aad-app-reg.sh) to register two apps

   - **TRE API:**  (with two roles `TREAdmin`, and `TREUser`) This app is used to authenticate users to the API - add users to the admin, and user roles.
   - **TRE Swagger UI**: This app is used to allow Swagger login
   - You will also want to create applications for workspaces (with the roles `WorkspaceResearcher` and `WorkspaceOwner`) that govern who can see what workspaces in the API


## Running the Management API

### Develop and run locally on Windows

1. Install python dependencies (in a virtual environment)

    ```cmd
    virtualenv venv
    venv/Scripts/activate
    pip install -r requirements.txt
    ```

1. Copy `.env.tmpl` in the **management_api_app** folder to `.env` and configure the variables
1. Start the web API

    ```cmd
    cd management_api_app
    uvicorn main:app --reload
    ```

The API will be available at [https://localhost:8000/docs](https://localhost:8000/docs) in your browser.

### Develop and run in a DevContainer

1. Open the project in Visual Studio Code in the DevContainer
1. Copy `.env.sample` in the **management_api_app** folder to `.env` and configure the variables
1. Start the web API

    ```cmd
    cd management_api_app
    pip install -r requirements.txt
    uvicorn main:app --reload
    ```

The API will be available at [https://localhost:8000/docs](https://localhost:8000/docs) in your browser.

### Deploy with docker

You must have docker and docker-compose tools installed, and an Azure Cosmos DB configured in `.env` as described above.

Then run:

```cmd
cd management_api_app
docker compose up -d app
```

The API will be available at [https://localhost:8000/api](https://localhost:8000/api) in your browser.

## Running the Resource Processor function

The Resource Processor is an Azure Function that can be hosted in [command line](https://docs.microsoft.com/en-us/azure/azure-functions/create-first-function-cli-python?tabs=azure-cli%2Cbash%2Cbrowser#run-the-function-locally)

```cmd
cd processor_function
func start
```

Or in [Visual Studio Code](https://docs.microsoft.com/en-us/azure/azure-functions/create-first-function-vs-code-python#run-the-function-in-azure).

## Run tests

Tests are written with pytest and located in folders:

- `/management_api_app/tests/`
- `/processor_function/tests/`

Run all tests with:

```cmd
pytest
```

## (Optional) Install pre-commit hooks

Pre commit hooks help you lint your python code on each git commit, to avoid having to fail the build when submitting a PR. Installing pre-commit hooks is completely optional.

```cmd
pre-commit install
```

## API Endpoints

API endpoints documentation and swagger are available at [https://localhost:8000/docs](https://localhost:8000/docs)

## Management API Project Structure

```text
management_api_app
├── api              - web related stuff.
│   ├── dependencies - dependencies for routes definition.
│   ├── errors       - definition of error handlers.
│   └── routes       - web routes.
├── core             - application configuration, startup events, logging.
├── db               - db related stuff.
│   ├── migrations   - manually written alembic migrations.
│   └── repositories - all crud stuff.
├── models           - pydantic models for this application.
│   ├── domain       - main models that are used almost everywhere.
│   └── schemas      - schemas for using in web routes.
├── resources        - strings that are used in web responses.
├── services         - logic that is not just crud related.
└── main.py          - FastAPI application creation and configuration.
```
