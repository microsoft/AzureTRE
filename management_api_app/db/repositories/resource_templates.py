import uuid
from typing import List

from azure.cosmos import CosmosClient
from pydantic import parse_obj_as

from core import config
from db.errors import EntityDoesNotExist
from db.repositories.base import BaseRepository
from models.domain.resource import ResourceType
from models.domain.resource_template import ResourceTemplate
from models.schemas.resource_template import ResourceTemplateInCreate, ResourceTemplateInformation


class ResourceTemplateRepository(BaseRepository):
    def __init__(self, client: CosmosClient):
        super().__init__(client, config.STATE_STORE_RESOURCE_TEMPLATES_CONTAINER)

    @staticmethod
    def _template_by_name_query(name: str, resource_type: ResourceType) -> str:
        return f'SELECT * FROM c WHERE c.resourceType = "{resource_type}" AND c.name = "{name}"'

    def get_templates_information(self, resource_type: ResourceType, parent_service_name: str = "") -> List[ResourceTemplateInformation]:
        """
        Returns name/description for all current resource_type templates
        """
        query = f'SELECT c.name, c.description FROM c WHERE c.resourceType = "{resource_type}" AND c.current = true'
        if resource_type == ResourceType.UserResource:
            query += f' AND c.parentWorkspaceService = "{parent_service_name}"'
        template_infos = self.query(query=query)
        return [parse_obj_as(ResourceTemplateInformation, info) for info in template_infos]

    def get_current_template(self, template_name: str, resource_type: ResourceType) -> ResourceTemplate:
        """
        Returns full template for the current version of the 'template_name' template
        """
        query = self._template_by_name_query(template_name, resource_type) + ' AND c.current = true'
        templates = self.query(query=query)
        if len(templates) != 1:
            raise EntityDoesNotExist
        return parse_obj_as(ResourceTemplate, templates[0])

    def get_template_by_name_and_version(self, name: str, version: str, resource_type: ResourceType) -> ResourceTemplate:
        """
        Returns full template for the 'resource_type' template defined by 'template_name' and 'version'
        """
        query = self._template_by_name_query(name, resource_type) + f' AND c.version = "{version}"'
        templates = self.query(query=query)
        if len(templates) != 1:
            raise EntityDoesNotExist
        return parse_obj_as(ResourceTemplate, templates[0])

    def create_template(self, template_input: ResourceTemplateInCreate, resource_type: ResourceType) -> ResourceTemplate:
        """
        creates a template based on the input (workspace and workspace-services template)
        """
        template = ResourceTemplate(
            id=str(uuid.uuid4()),
            name=template_input.name,
            description=template_input.json_schema["description"],
            version=template_input.version,
            resourceType=resource_type,
            current=template_input.current,
            required=template_input.json_schema["required"],
            properties=template_input.json_schema["properties"],
        )
        self.save_item(template)
        return template
