# Developer Setup

- [Develop and run locally on Windows](#develop-and-run-locally-on-windows)
- [Develop and run in a DevContainer](#develop-and-run-in-a-devcontainer)
- [Deploy with docker](#deploy-with-docker)
- [Run tests](#run-tests)
- [(Optional) Install pre-commit hooks](#optional-install-pre-commit-hooks)
- [API Endpoints](#api-endpoints)
- [Project Structure](#project-structure)

## Develop and run locally on Windows

1. [Install the Cosmos DB Emulator](https://docs.microsoft.com/en-us/azure/cosmos-db/local-emulator?tabs=cli%2Cssl-netstd21)
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

The API will be available at [https://localhost:8000/api](https://localhost:8000/api) in your browser.

## Develop and run in a DevContainer

1. [Create a Cosmos DB Database in Azure](https://docs.microsoft.com/en-us/azure/cosmos-db/create-cosmosdb-resources-portal)
1. Open the project in Visual Studio Code in the DevContainer
1. Copy `.env.tmpl` in the **core** folder to `.env` and configure the variables
1. Start the web API

    ```cmd
    cd management_api_app
    uvicorn main:app --reload
    ```

The API will be available at [https://localhost:8000/api](https://localhost:8000/api) in your browser.

## Deploy with docker

You must have docker and docker-compose tools installed, and an Azure Cosmos DB configured in `.env` as described above.

Then run:

```cmd
cd management_api_app
docker compose up -d app
```

The API will be available at [https://localhost:8000/api](https://localhost:8000/api) in your browser.

## Run tests

Tests are written with pytest and located in the `tests` folder

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

## Project Structure

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
