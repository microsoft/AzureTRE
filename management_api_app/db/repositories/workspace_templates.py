import uuid
from typing import List

from azure.cosmos import CosmosClient
from pydantic import parse_obj_as

from core import config
from db.errors import EntityDoesNotExist
from db.repositories.base import BaseRepository
from models.domain.resource import ResourceType
from models.domain.resource_template import ResourceTemplate
from models.schemas.workspace_template import WorkspaceTemplateInCreate


class WorkspaceTemplateRepository(BaseRepository):
    def __init__(self, client: CosmosClient):
        super().__init__(client, config.STATE_STORE_RESOURCE_TEMPLATES_CONTAINER)

    @staticmethod
    def _workspace_template_by_name_query(name: str) -> str:
        return f'SELECT * FROM c WHERE c.resourceType = "workspace" AND c.name = "{name}"'

    def get_workspace_templates_by_name(self, name: str) -> List[ResourceTemplate]:
        query = self._workspace_template_by_name_query(name)
        resource_templates = self.query(query=query)
        print(resource_templates)
        return parse_obj_as(List[ResourceTemplate], resource_templates)

    def get_current_workspace_template_by_name(self, name: str) -> ResourceTemplate:
        query = self._workspace_template_by_name_query(name) + ' AND c.current = true'
        workspace_templates = self.query(query=query)
        print(workspace_templates)
        if len(workspace_templates) != 1:
            raise EntityDoesNotExist
        return parse_obj_as(ResourceTemplate, workspace_templates[0])

    def get_workspace_template_by_name_and_version(self, name: str, version: str) -> ResourceTemplate:
        query = self._workspace_template_by_name_query(name) + f' AND c.version = "{version}"'
        workspace_templates = self.query(query=query)
        if len(workspace_templates) != 1:
            raise EntityDoesNotExist
        return parse_obj_as(ResourceTemplate, workspace_templates[0])

    def get_workspace_template_names(self) -> List[str]:
        query = 'SELECT c.name FROM c'
        workspace_templates = self.query(query=query)
        workspace_template_names = [template["name"] for template in workspace_templates]
        return list(set(workspace_template_names))

    def create_workspace_template_item(self, workspace_template_create: WorkspaceTemplateInCreate) -> ResourceTemplate:
        item_id = str(uuid.uuid4())
        resource_template = ResourceTemplate(
            id=item_id,
            name=workspace_template_create.name,
            description=workspace_template_create.description,
            version=workspace_template_create.version,
            parameters=workspace_template_create.parameters,
            resourceType=ResourceType.Workspace,
            current=workspace_template_create.current,
        )
        self.create_item(resource_template)
        return resource_template

    def update_item(self, resource_template: ResourceTemplate):
        self.container.upsert_item(resource_template.dict())
