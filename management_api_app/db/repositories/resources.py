from azure.cosmos import CosmosClient
from pydantic import UUID4

from core import config
from db.errors import EntityDoesNotExist
from db.repositories.base import BaseRepository
from jsonschema import validate


class ResourceRepository(BaseRepository):
    def __init__(self, client: CosmosClient):
        super().__init__(client, config.STATE_STORE_RESOURCES_CONTAINER)

    @staticmethod
    def _validate_resource_parameters(workspace_create, workspace_template):
        validate(instance=workspace_create["properties"], schema=workspace_template)

    def get_resource_dict_by_id(self, workspace_id: UUID4) -> dict:
        query = self._active_workspaces_query() + f' AND c.id="{workspace_id}"'
        workspaces = self.query(query=query)
        if not workspaces:
            raise EntityDoesNotExist
        return workspaces[0]

    def update_resource_dict(self, resource_dict: dict):
        self.container.upsert_item(body=resource_dict)