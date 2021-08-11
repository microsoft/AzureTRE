import uuid
from typing import List

from azure.cosmos import CosmosClient
from pydantic import parse_obj_as

from core import config
from db.errors import EntityDoesNotExist
from db.repositories.base import BaseRepository
from models.domain.resource import ResourceType
from models.domain.resource_template import ResourceTemplate
from models.schemas.resource_template import ResourceTemplateInCreate


class ResourceTemplateRepository(BaseRepository):
    def __init__(self, client: CosmosClient):
        super().__init__(client, config.STATE_STORE_RESOURCE_TEMPLATES_CONTAINER)

    @staticmethod
    def _resource_template_by_name_query(name: str, resource_type: str = ResourceType.Workspace) -> str:
        return f'SELECT * FROM c WHERE c.resourceType = "{resource_type}" AND c.name = "{name}"'

    def get_workspace_templates_by_name(self, name: str) -> List[ResourceTemplate]:
        query = self._resource_template_by_name_query(name)
        resource_templates = self.query(query=query)
        return parse_obj_as(List[ResourceTemplate], resource_templates)

    def get_current_resource_template_by_name(self, name: str, resource_type: str = ResourceType.Workspace) -> ResourceTemplate:
        query = self._resource_template_by_name_query(name, resource_type) + ' AND c.current = true'
        workspace_templates = self.query(query=query)
        if len(workspace_templates) != 1:
            raise EntityDoesNotExist
        return parse_obj_as(ResourceTemplate, workspace_templates[0])

    def get_resource_template_by_name_and_version(self, name: str, version: str, resource_type: str = ResourceType.Workspace) -> ResourceTemplate:
        query = self._resource_template_by_name_query(name, resource_type) + f' AND c.version = "{version}"'
        resource_templates = self.query(query=query)
        if len(resource_templates) != 1:
            raise EntityDoesNotExist
        return parse_obj_as(ResourceTemplate, resource_templates[0])

    def get_workspace_template_names(self) -> List[str]:
        query = 'SELECT c.name FROM c'
        workspace_templates = self.query(query=query)
        workspace_template_names = [template["name"] for template in workspace_templates]
        return list(set(workspace_template_names))

    def create_resource_template_item(self, template_create: ResourceTemplateInCreate,
                                      resource_type: ResourceType) -> ResourceTemplate:
        item_id = str(uuid.uuid4())
        description = template_create.json_schema["description"]
        required = template_create.json_schema["required"]
        properties = template_create.json_schema["properties"]
        resource_template = ResourceTemplate(
            id=item_id,
            name=template_create.name,
            description=description,
            version=template_create.version,
            resourceType=resource_type,
            current=template_create.current,
            required=required,
            properties=properties
        )
        self.create_item(resource_template)
        return resource_template

    def update_item(self, resource_template: ResourceTemplate):
        self.container.upsert_item(resource_template.dict())
