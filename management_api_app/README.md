# Management API

> TBD: General description

## API endpoints

API endpoints documentation and the Swagger UI are available at [https://localhost:8000/docs](https://localhost:8000/docs).

## Structure

```text
management_api_app
├── api              - web related stuff
│   ├── dependencies - dependencies for routes definition
│   ├── errors       - definition of error handlers
│   └── routes       - web routes
├── core             - application configuration, startup events, logging
├── db               - db related stuff
│   ├── migrations   - manually written alembic migrations
│   └── repositories - all crud stuff
├── models           - pydantic models for this application
│   ├── domain       - main models that are used almost everywhere
│   └── schemas      - schemas for using in web routes
├── resources        - strings that are used in web responses
├── services         - logic that is not just crud related
├── tests_ma         - unit tests
└── main.py          - FastAPI application creation and configuration
```

## Prerequisites

> TBD

## Configuration

### General

| Environment variable name | Description |
| ------------------------- | ----------- |
| `DEBUG` | When set to `True`, the debugging information for unhandled exceptions is shown in the Swagger UI and logging is more verbose. |
| `TRE_ID` | The Azure TRE instance name - used for deployment of resources (can be set to anything when debugging locally). Example value: `mytre-dev-3142` |
| `RESOURCE_LOCATION` | The location (region) to deploy resources (e.g., workspaces) to. This can be set to anything as the deployment service is not called locally. Example value: `westeurope` |

### Auth

Management API depends on [TRE API](#tre-api) and [TRE Swagger UI](#tre-swagger-ui) app registrations. The API requires the environment variables listed in the table below to be present. See [Authentication and authorization](../docs/auth.md) for more information.

| Environment variable name | Description |
| ------------------------- | ----------- |
| `AAD_TENANT_ID` | The tenant ID of the Azure AD. |
| `API_CLIENT_ID` | The application (client) ID of the [TRE API](../docs/auth.md#tre-api) service principal. |
| `API_CLIENT_SECRET` | The application password (client secret) of the [TRE API](../docs/auth.md#tre-api) service principal. |
| `SWAGGER_UI_CLIENT_ID` | The application (client) ID of the [TRE Swagger UI](../docs/auth.md#tre-swagger-ui) service principal. |

### State store

| Environment variable name | Description |
| ------------------------- | ----------- |
| `STATE_STORE_ENDPOINT` | The Cosmos DB endpoint. Use `localhost` with an emulator. Example value: `https://localhost:8081` |
| `STATE_STORE_KEY` | The Cosmos DB access key. |

### Service Bus

| Environment variable name | Description |
| ------------------------- | ----------- |
| `SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE` | Example value: `<your namespace>.servicebus.windows.net` |
| `SERVICE_BUS_RESOURCE_REQUEST_QUEUE` | The queue for resource request messages sent by the API. Example value: `workspacequeue` |
| `SERVICE_BUS_DEPLOYMENT_STATUS_UPDATE_QUEUE` | The queue for deployment status update messages sent by [Resource Processor Function](../processor_function/README.md) and received by the API. Example value: `deploymentstatus` |

### Logging and monitoring

| Environment variable name | Description |
| ------------------------- | ----------- |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | Application Insights connection string - can be left blank when debugging locally. |
| `APPINSIGHTS_INSTRUMENTATIONKEY` | pplication Insights instrumentation key - can be left blank when debugging locally. |

### Service principal for API process identity

| Environment variable name | Description |
| ------------------------- | ----------- |
| `AZURE_SUBSCRIPTION_ID` |  |
| `AZURE_TENANT_ID` |  |
| `AZURE_CLIENT_ID` |  |
| `AZURE_CLIENT_SECRET` |  |

## Running Management API

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

## Auth in code

The bulk of the authentication and authorization (A&A) related code of Management API is located in `/management_api_app/services/` folder. The A&A code has an abstract base for enabling the possibility to add additional A&A service providers. The Azure Active Directory (AAD) specific implementation is derived as follows:

```plaintext
AccessService (access_service.py) <─── AADAccessService (aad_access_service.py)

fastapi.security.OAuth2AuthorizationCodeBearer <─── AzureADAuthorization (aad_authentication.py)
```

All the sensitive routes (API calls that can query sensitive data or modify resources) in Management API depend on having a "current user" authenticated. E.g., in [`/management_api_app/api/routes/workspaces.py`](./api/routes/workspaces.py):

```python
router = APIRouter(dependencies=[Depends(get_current_user)])
```

Where `APIRouter` is part of the [FastAPI](https://fastapi.tiangolo.com/).

The user details, once authenticated, are stored as an instance of the custom [User](./services/authentication.py) class.

## Workspace requests

Some workspace routes require `authConfig` field in the request body. The AAD specific implementation expects a dictionary inside `data` field to contain the application (client) ID of the [app registration associated with workspace](../docs/auth.md#workspaces):

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

> **Note:** The app registration for a workspace is not created by the API. One needs to be present (created manually) before using the API to provision a new workspace.