import logging

from azure.cosmos import CosmosClient
from fastapi import FastAPI

from core.config import STATE_STORE_ENDPOINT, STATE_STORE_KEY


async def close_db_connection(app: FastAPI) -> None:
    return None


async def connect_to_db(app: FastAPI) -> None:
    logging.debug(f"Connecting to {STATE_STORE_ENDPOINT}")

    try:
        cosmos_client = CosmosClient(STATE_STORE_ENDPOINT, STATE_STORE_KEY)
        app.state.cosmos_client = cosmos_client
        logging.debug("Connection established")
    except Exception as e:
        logging.debug(f"Connection to state store could not be established: {e}")
