# TRE API

The TRE API is a service that users can interact with to request changes to workspaces e.g., to create, update, delete workspaces and workspace services inside each workspace.

## Prerequisites

### Tools

* [Python](https://www.python.org/downloads/) >= 3.8 with [pip](https://packaging.python.org/tutorials/installing-packages/#ensure-you-can-run-pip-from-the-command-line)

### Azure resources

* [Application Insights](https://docs.microsoft.com/azure/azure-monitor/app/app-insights-overview) - Not required for testing locally
* [Azure Cosmos DB](https://docs.microsoft.com/azure/cosmos-db/introduction) (SQL)
  * You can use the [Cosmos DB Emulator](https://docs.microsoft.com/azure/cosmos-db/local-emulator?tabs=cli%2Cssl-netstd21) for testing locally
* [Azure Service Bus](https://docs.microsoft.com/azure/service-bus-messaging/service-bus-messaging-overview)
* Service principal for the API to access Azure services such as Azure Service Bus
* AAD applications (for the API and Swagger UI) - see [Authentication & authorization](../tre-admins/auth.md) for more information

#### Creating resources (Bash)

The following snippets can be used to create resources for local testing with Bash shell.

Sign in with Azure CLI:

```cmd
az login
az account list
az account set --subscription <subscription ID>
```

Provision Azure Service Bus:

```bash
RESOURCE_GROUP=<resource group name>
LOCATION=westeurope
SERVICE_BUS_NAMESPACE=<service bus namespace name>
SERVICE_BUS_RESOURCE_REQUEST_QUEUE=workspacequeue
SERVICE_BUS_DEPLOYMENT_STATUS_UPDATE_QUEUE=deploymentstatus

az servicebus namespace create --resource-group $RESOURCE_GROUP --name $SERVICE_BUS_NAMESPACE --location $LOCATION
az servicebus queue create --resource-group $RESOURCE_GROUP --namespace-name $SERVICE_BUS_NAMESPACE --name $SERVICE_BUS_RESOURCE_REQUEST_QUEUE
az servicebus queue create --resource-group $RESOURCE_GROUP --namespace-name $SERVICE_BUS_NAMESPACE --name $SERVICE_BUS_DEPLOYMENT_STATUS_UPDATE_QUEUE
```

Provision Azure Cosmos DB:

```bash
COSMOS_NAME=<cosmos_name>
COSMOS_DB_NAME=<database_name>

az cosmosdb create -n $COSMOS_NAME -g $RESOURCE_GROUP --locations regionName=$LOCATION
az cosmosdb sql database create -a $COSMOS_NAME -g $RESOURCE_GROUP -n $COSMOS_DB_NAME
```

[Create a service principal](https://docs.microsoft.com/en-us/cli/azure/create-an-azure-service-principal-azure-cli) and assign it permissions to access Service Bus:

```bash
az ad sp create-for-rbac --name <service principal name>

SERVICE_PRINCIPAL_ID=<the AppId of the Service Principal>
SUBSCRIPTION_ID=$(az account show --query id --output tsv)

az role assignment create \
    --role "Azure Service Bus Data Sender" \
    --assignee $SERVICE_PRINCIPAL_ID \
    --scope /subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.ServiceBus/namespaces/$SERVICE_BUS_NAMESPACE

az role assignment create \
    --role "Azure Service Bus Data Receiver" \
    --assignee $SERVICE_PRINCIPAL_ID \
    --scope /subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.ServiceBus/namespaces/$SERVICE_BUS_NAMESPACE
```

!!! caution
    Keep in mind that Azure role assignments may take up to five minutes to propagate.

## Configuration

### General

| <div style="width: 340px">Environment variable name</div> | Description |
| ------------------------- | ----------- |
| `DEBUG` | When set to `True`, the debugging information for unhandled exceptions is shown in the Swagger UI and logging is more verbose. |
| `TRE_ID` | The Azure TRE instance name - used for deployment of resources (can be set to anything when debugging locally). Example value: `mytre-dev-3142` |
| `RESOURCE_LOCATION` | The location (region) to deploy resources (e.g., workspaces) to. This can be set to anything as the deployment service is not called locally. Example value: `westeurope` |

### Authentication and Authorization

The TRE API depends on [TRE API](../tre-admins/auth.md#tre-api) and [TRE Swagger UI](../tre-admins/auth.md#tre-swagger-ui) app registrations. The API requires the environment variables listed in the table below to be present. See [Authentication and authorization](../tre-admins/auth.md) for more information.

| <div style="width: 340px">Environment variable name</div> | Description |
| ------------------------- | ----------- |
| `AAD_TENANT_ID` | The tenant ID of the Azure AD. |
| `API_CLIENT_ID` | The application (client) ID of the [TRE API](../tre-admins/auth.md#tre-api) service principal. |
| `API_CLIENT_SECRET` | The application password (client secret) of the [TRE API](../tre-admins/auth.md#tre-api) service principal. |
| `SWAGGER_UI_CLIENT_ID` | The application (client) ID of the [TRE Swagger UI](../tre-admins/auth.md#tre-swagger-ui) service principal. |

See also: [Auth in code](#auth-in-code)

### State store

| <div style="width: 340px">Environment variable name</div> | Description |
| ------------------------- | ----------- |
| `STATE_STORE_ENDPOINT` | The Cosmos DB endpoint. Use `localhost` with an emulator. Example value: `https://localhost:8081` |
| `STATE_STORE_KEY` | The Cosmos DB key. Use only with localhost emulator. |
| `COSMOSDB_ACCOUNT_NAME` | The Cosmos DB account name. |
| `SUBSCRIPTION_ID` | The Azure Subscription ID where Cosmos DB is located. |
| `RESOURCE_GROUP_NAME` | The Azure Resource Group name where Cosmos DB is located. |

### Service Bus

| <div style="width: 340px">Environment variable name</div> | Description |
| ------------------------- | ----------- |
| `SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE` | Example value: `<your namespace>.servicebus.windows.net` |
| `SERVICE_BUS_RESOURCE_REQUEST_QUEUE` | The queue for resource request messages sent by the API. Example value: `workspacequeue` |
| `SERVICE_BUS_DEPLOYMENT_STATUS_UPDATE_QUEUE` | The queue for deployment status update messages sent by [Resource Processor](resource-processor.md) and received by the API. Example value: `deploymentstatus` |

### Logging and monitoring

| <div style="width: 340px">Environment variable name</div> | Description |
| ------------------------- | ----------- |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | Application Insights connection string - can be left blank when debugging locally. |
| `APPINSIGHTS_INSTRUMENTATIONKEY` | Application Insights instrumentation key - can be left blank when debugging locally. |

### Service principal for API process identity

| <div style="width: 340px">Environment variable name</div> | Description |
| ------------------------- | ----------- |
| `AZURE_SUBSCRIPTION_ID` | Azure Subscription ID |
| `AZURE_TENANT_ID` | Azure Tenant ID |
| `AZURE_CLIENT_ID` | API Service Principal ID |
| `AZURE_CLIENT_SECRET` | API Service Principal Secret |

## Running the API

### Develop and run locally

1. Install python dependencies (in a virtual environment)

    ```cmd
    virtualenv venv
    venv/Scripts/activate
    pip install -r requirements.txt
    ```

1. Copy `.env.tmpl` in the **api_app** folder to `.env` and configure the variables. Notice: You might also need to export those variables to your env (`export VAR_NAME=VALUE` for all vars in the .env file).
1. Start the web API

    ```cmd
    cd api_app
    uvicorn main:app --reload
    ```

The API endpoints documentation and the Swagger UI will be available at [https://localhost:8000/api/docs](https://localhost:8000/api/docs).

### Develop and run in a dev container

1. Open the project in Visual Studio Code in the DevContainer
1. Copy `.env.sample` in the **api_app** folder to `.env` and configure the variables
1. Start the web API

    ```cmd
    cd api_app
    pip install -r requirements.txt
    pip install -r requirements-dev.txt
    uvicorn main:app --reload
    ```

The API endpoints documentation and the Swagger UI will be available at [https://localhost:8000/api/docs](https://localhost:8000/api/docs).

### Deploy with Docker

You must have Docker and Docker Compose tools installed, and an Azure Cosmos DB configured in `.env` as described above.

Then run:

```cmd
cd api_app
docker compose up -d app
```

The API will be available at [https://localhost:8000/api](https://localhost:8000/api) in your browser.

## Unit tests

The unit tests are written with pytest and located in folder `/api_app/tests_ma/`.

Run all unit tests with the following command in the root folder of the repository:

```cmd
pytest --ignore=e2e_tests
```

## API application folder structure

```text
api_app
├── api              - API implementation
│   ├── dependencies - Dependencies for routes definition
│   ├── errors       - Definitions of error handlers
│   └── routes       - Web routes (API endpoints)
│
├── core             - Application configuration, startup events, logging
│
├── db               - Database related implementation
│   ├── migrations   - Manually written alembic migrations
│   └── repositories - All CRUD features
│
├── models           - Pydantic models for this application
│   ├── domain       - Main models that are used almost everywhere
│   └── schemas      - Schemas for using in web routes
│
├── resources        - Strings that are used e.g., in web responses
│
├── services         - Logic that is not only CRUD related
│
├── tests_ma         - Unit tests
│
└── main.py          - FastAPI application creation and configuration
```

## Auth in code

The bulk of the authentication and authorization (A&A) related code of the API is located in `/api_app/services/` folder. The A&A code has an abstract base for enabling the possibility to add additional A&A service providers. The Azure Active Directory (AAD) specific implementation is derived as follows:

```plaintext
AccessService (access_service.py) <─── AADAccessService (aad_access_service.py)

fastapi.security.OAuth2AuthorizationCodeBearer <─── AzureADAuthorization (aad_authentication.py)
```

All the sensitive routes (API calls that can query sensitive data or modify resources) in the TRE API depend on having a "current user" authenticated. E.g., in `/api_app/api/routes/workspaces.py`:

```python
router = APIRouter(dependencies=[Depends(get_current_user)])
```

Where `APIRouter` is part of the [FastAPI](https://fastapi.tiangolo.com/).

The user details, once authenticated, are stored as an instance of the custom `User` class.

## Auth in workspace requests

Some workspace routes require `authConfig` field in the request body. The AAD specific implementation expects a dictionary inside `data` field to contain the application (client) ID of the [app registration associated with workspace](../tre-admins/auth.md#workspaces):

```json
{
  "authConfig": {
    "provider": "AAD",
    "data": {
      "app_id": "c36f2ee3-8ec3-4431-9240-b1c0a0eb80a0"
    }
  }
}
```

!!! caution
    The app registration for a workspace is not created by the API. One needs to be present (created manually) before using the API to provision a new workspace.

## Network requirements

To be able to run the TRE API it needs to access the following resource outside the Azure TRE VNET via explicit allowed [Service Tags](https://docs.microsoft.com/en-us/azure/virtual-network/service-tags-overview) or URLs.

| Service Tag / Destination | Justification |
| --- | --- |
| AzureActiveDirectory | Authenticate with the User Assigned identity to access Azure Cosmos DB and Azure Service Bus. |
| AzureResourceManager | To perform control plane operations, such as create database in State Store. |
| AzureContainerRegistry | Pull the TRE API container image, as it is located in Azure Container Registry.  |
| graph.microsoft.com | Lookup role assignments for Azure Active Directory user, to only show TRE resources and user has access to. |
