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

> TBD

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
