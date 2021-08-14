from azure.cosmos import CosmosClient
from jsonschema import validate
from pydantic import UUID4

from core import config
from db.errors import EntityDoesNotExist
from db.repositories.base import BaseRepository


class ResourceRepository(BaseRepository):
    def __init__(self, client: CosmosClient):
        super().__init__(client, config.STATE_STORE_RESOURCES_CONTAINER)

    @staticmethod
    def _active_resources_query():
        return 'SELECT * FROM c WHERE c.deleted = false'

    @staticmethod
    def _validate_resource_parameters(resource_create, resource_template):
        validate(instance=resource_create["properties"], schema=resource_template)

    def get_resource_dict_by_id(self, resource_id: UUID4) -> dict:
        query = self._active_resources_query() + f' AND c.id="{resource_id}"'
        resources = self.query(query=query)
        if not resources:
            raise EntityDoesNotExist
        return resources[0]

    def update_resource_dict(self, resource_dict: dict):
        self.container.upsert_item(body=resource_dict)

    def delete_resource(self, resource_id: str):
        self.container.delete_item(item=resource_id, partition_key=resource_id)
