from azure.cosmos import CosmosClient
from datetime import datetime
from jsonschema import validate
from pydantic import UUID4
import copy

from core import config
from db.errors import EntityDoesNotExist
from db.repositories.base import BaseRepository
from db.repositories.resource_templates import ResourceTemplateRepository
from models.domain.resource import Resource, ResourceHistoryItem, ResourceType
from models.domain.resource_template import ResourceTemplate
from models.schemas.resource import ResourcePatch


class ResourceRepository(BaseRepository):
    def __init__(self, client: CosmosClient):
        super().__init__(client, config.STATE_STORE_RESOURCES_CONTAINER)

    @staticmethod
    def _active_resources_query():
        # get active docs (not deleted)
        return f'SELECT * FROM c WHERE {IS_ACTIVE_CLAUSE}'

    def _active_resources_by_type_query(self, resource_type: ResourceType):
        return self._active_resources_query() + f' AND c.resourceType = "{resource_type}"'

    def _active_resources_by_id_query(self, resource_id: str):
        return self._active_resources_query() + f' AND c.id = "{resource_id}"'

    @staticmethod
    def _validate_resource_parameters(resource_input, resource_template):
        validate(instance=resource_input["properties"], schema=resource_template)

    def _get_enriched_template(self, template_name: str, resource_type: ResourceType, parent_template_name: str = ""):
        template_repo = ResourceTemplateRepository(self._client)
        template = template_repo.get_current_template(template_name, resource_type, parent_template_name)
        return template_repo.enrich_template(template)

    @staticmethod
    def get_resource_base_spec_params():
        return {"tre_id": config.TRE_ID}

    def get_resource_dict_by_id(self, resource_id: UUID4) -> dict:
        query = self._active_resources_by_id_query(str(resource_id))
        resources = self.query(query=query)
        if not resources:
            raise EntityDoesNotExist
        return resources[0]

    def validate_input_against_template(self, template_name: str, resource_input, resource_type: ResourceType, parent_template_name: str = "") -> str:
        try:
            template = self._get_enriched_template(template_name, resource_type, parent_template_name)
            template_version = template["version"]
        except EntityDoesNotExist:
            if resource_type == ResourceType.UserResource:
                raise ValueError(f'The template "{template_name}" does not exist or is not valid for the workspace service type "{parent_template_name}"')
            else:
                raise ValueError(f'The template "{template_name}" does not exist')

        self._validate_resource_parameters(resource_input.dict(), template)

        return template_version

    def patch_resource(self, resource: Resource, resource_patch: ResourcePatch, resource_template: ResourceTemplate, etag: str) -> Resource:

        # create a deep copy of the resource to use for history, create the history item + add to history list
        resource_copy = copy.deepcopy(resource)
        history_item = ResourceHistoryItem(
            isEnabled=resource_copy.isEnabled,
            properties=resource_copy.properties,
            resourceVersion=resource_copy.resourceVersion,
            updatedWhen=get_timestamp()
        )
        resource.history.append(history_item)

        # now update the resource props
        resource.resourceVersion = resource.resourceVersion + 1

        if resource_patch.isEnabled is not None:
            resource.isEnabled = resource_patch.isEnabled

        # TODO -> (https://github.com/microsoft/AzureTRE/issues/1240) -> validate updated resource props here. For now - just union the 2 property dicts
        if resource_patch.properties is not None and len(resource_patch.properties) > 0:
            resource.properties.update(resource_patch.properties)

        return self.update_item_with_etag(resource, etag)


def get_timestamp() -> float:
    return datetime.utcnow().timestamp()


# Cosmos query consts
IS_ACTIVE_CLAUSE = 'c.isActive != false'
