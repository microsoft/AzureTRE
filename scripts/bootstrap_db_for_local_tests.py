"""
This script adds resources to your cosmos database for local, manual, testing purposes
NOTE: This script is not required for the tests to run, but assists in creating resources to test the API manually
"""
import uuid

from azure.cosmos import CosmosClient, PartitionKey
from starlette.config import Config


config = Config("../management_api_app/.env")
STATE_STORE_ENDPOINT: str = config("STATE_STORE_ENDPOINT", default="")  # cosmos db endpoint
STATE_STORE_KEY: str = config("STATE_STORE_KEY", default="")  # cosmos db access key
STATE_STORE_DATABASE = "AzureTRE"
STATE_STORE_RESOURCES_CONTAINER = "Resources"


def create_workspace_resource(resource_id: str):
    return {
        "id": resource_id,
        "resourceSpec": {
            "name": "tre-workspace-vanilla",
            "version": "0.1.0"
        },
        "parameters": {
            "location": "europe"
        },
        "resourceType": "workspace",
        "status": "not_deployed",
        "isDeleted": False
    }


def main():
    client = CosmosClient(STATE_STORE_ENDPOINT, STATE_STORE_KEY)
    database = client.create_database_if_not_exists(STATE_STORE_DATABASE)

    for container in database.list_containers():
        database.delete_container(container["id"])

    container = database.create_container_if_not_exists(STATE_STORE_RESOURCES_CONTAINER, partition_key=PartitionKey(path="/appId"), offer_throughput=400)

    # Create workspace resources
    for _ in range(3):
        container.create_item(body=create_workspace_resource(str(uuid.uuid4())))


if __name__ == "__main__":
    main()
