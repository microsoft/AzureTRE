import uuid
import logging

from azure.cosmos import CosmosClient, PartitionKey, DatabaseProxy
from fastapi import FastAPI

from core import config


async def connect_to_db(app: FastAPI) -> None:
    logging.debug(f"Connecting to {config.STATE_STORE_ENDPOINT}")

    try:
        cosmos_client = CosmosClient(config.STATE_STORE_ENDPOINT, config.STATE_STORE_KEY, connection_verify=False)
        app.state.cosmos_client = cosmos_client
        logging.debug("Connection established")
    except Exception as e:
        logging.debug(f"Connection to state store could not be established: {e}")

# Bootstrapping is temporary while the API does not have a register spec api implemented.


async def create_bundle_registry(database: DatabaseProxy):
    """
    Creates a bundle spec container if one does not exist and populate it with a canonical spec.
    :param database: DatabaseProxy for STATE_STORE_DATABASE
    :returns: None
    """
    bundle_spec = {
        "url": "blah/blah:v1",
        "id": str(uuid.uuid4()),
        "fields": [
            {"name": "location", "required": True},
            {"name": "tre_id", "required": True},
            {"name": "workspace_id", "required": True},
            {"name": "address_space", "required": True}
        ]
    }

    bundle_specs = [bundle_spec]
    container_name = config.STATE_STORE_BUNDLE_SPECS_CONTAINER

    containers = list(database.query_containers(
        {
            "query": "SELECT * FROM r WHERE r.id=@id",
            "parameters": [
                {"name": "@id", "value": container_name}
            ]
        }
    ))

    if not len(containers):
        container = database.create_container_if_not_exists(
            id=container_name,
            partition_key=PartitionKey(path="/url"),
            offer_throughput=400
        )
        for spec in bundle_specs:
            container.create_item(body=spec)


async def bootstrap_database(app: FastAPI) -> None:
    client: CosmosClient = app.state.cosmos_client
    if client:
        database_proxy = client.create_database_if_not_exists(id=config.STATE_STORE_DATABASE)
        await create_bundle_registry(database_proxy)
