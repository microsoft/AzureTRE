import logging

from azure.cosmos import CosmosClient
from fastapi import FastAPI

from core.config import STATE_STORE_ENDPOINT, STATE_STORE_KEY


async def close_db_connection(app: FastAPI) -> None:
    logging.info(f"Connecting to {STATE_STORE_ENDPOINT}")
    app.state.cosmos_client = CosmosClient(STATE_STORE_ENDPOINT, STATE_STORE_KEY)
    logging.info("Connection established")


async def connect_to_db(app: FastAPI) -> None:
    return None
