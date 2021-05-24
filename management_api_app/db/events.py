import logging

from azure.cosmos import CosmosClient, PartitionKey
from fastapi import FastAPI

from core.config import STATE_STORE_ENDPOINT, STATE_STORE_KEY


async def close_db_connection(app: FastAPI) -> None:
    return None


async def connect_to_db(app: FastAPI) -> None:
    logging.info(f"Connecting to {STATE_STORE_ENDPOINT}")
    cosmos_client = CosmosClient(STATE_STORE_ENDPOINT, STATE_STORE_KEY)
    database_name = "AzureTREDatabase"
    container_name = "WorkflowsContainer"
    api_db = cosmos_client.create_database_if_not_exists(database_name)
    workflows_container = api_db.create_container_if_not_exists(container_name, partition_key=PartitionKey(path="/workflow"))
    app.state.cosmos_client = cosmos_client
    app.state.api_db = api_db
    app.state.workflows_container = workflows_container
    logging.info("Connection established")
