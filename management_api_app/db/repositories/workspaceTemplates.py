from typing import List

from azure.cosmos import CosmosClient

from core import config
from db.errors import EntityDoesNotExist
from db.repositories.base import BaseRepository
from models.domain.resource_template import ResourceTemplate


class WorkspaceTemplateRepository(BaseRepository):
    def __init__(self, client: CosmosClient):
        super().__init__(client, config.STATE_STORE_RESOURCE_TEMPLATES_CONTAINER)

    @staticmethod
    def _workspace_template_by_name_query(name: str) -> str:
        return f'SELECT * FROM c WHERE c.resourceType = "workspace" AND c.name = {name}'

    def get_workspace_templates_by_name(self, name: str) -> List[ResourceTemplate]:
        query = self._workspace_template_by_name_query(name)
        return self._query(query=query)

    def get_current_workspace_template_by_name(self, name: str) -> ResourceTemplate:
        query = self._workspace_template_by_name_query(name) + ' AND c.isCurrent = true'
        workspace_templates = self._query(query=query)
        if len(workspace_templates) != 1:
            raise EntityDoesNotExist
        return workspace_templates[0]

    def get_workspace_template_by_name_and_version(self, name: str, version: str) -> ResourceTemplate:
        query = self._workspace_template_by_name_query(name) + ' AND c.version = {version}'
        workspace_templates = self._query(query=query)
        if len(workspace_templates) != 1:
            raise EntityDoesNotExist
        return workspace_templates[0]
