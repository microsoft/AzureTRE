import copy
from datetime import datetime
from typing import Tuple

from azure.cosmos import CosmosClient
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from core import config
from db.errors import EntityDoesNotExist
from db.repositories.base import BaseRepository
from db.repositories.resource_templates import ResourceTemplateRepository
from jsonschema import validate
from models.domain.authentication import User
from models.domain.resource import Resource, ResourceHistoryItem, ResourceType
from models.domain.resource_template import ResourceTemplate
from models.domain.shared_service import SharedService
from models.domain.operation import Status
from models.domain.user_resource import UserResource
from models.domain.workspace import Workspace
from models.domain.workspace_service import WorkspaceService
from models.schemas.resource import ResourcePatch
from pydantic import UUID4, parse_obj_as


class ResourceRepository(BaseRepository):
    def __init__(self, client: CosmosClient):
        super().__init__(client, config.STATE_STORE_RESOURCES_CONTAINER)

    @staticmethod
    def _active_resources_query():
        # get active docs (not deleted)
        return f'SELECT * FROM c WHERE {IS_NOT_DELETED_CLAUSE}'

    def _active_resources_by_type_query(self, resource_type: ResourceType):
        return self._active_resources_query() + f' AND c.resourceType = "{resource_type}"'

    def _active_resources_by_id_query(self, resource_id: str):
        return self._active_resources_query() + f' AND c.id = "{resource_id}"'

    @staticmethod
    def _validate_resource_parameters(resource_input, resource_template):
        validate(instance=resource_input["properties"], schema=resource_template)

    def _get_enriched_template(self, template_name: str, resource_type: ResourceType, parent_template_name: str = "") -> dict:
        template_repo = ResourceTemplateRepository(self._client)
        template = template_repo.get_current_template(template_name, resource_type, parent_template_name)
        return template_repo.enrich_template(template)

    @staticmethod
    def get_resource_base_spec_params():
        return {"tre_id": config.TRE_ID}

    def get_resource_dict_by_id(self, resource_id: UUID4) -> dict:
        try:
            resource = self.read_item_by_id(str(resource_id))
        except CosmosResourceNotFoundError:
            raise EntityDoesNotExist
        return resource

    def get_resource_by_id(self, resource_id: UUID4) -> Resource:
        resource = self.get_resource_dict_by_id(resource_id)

        if resource["resourceType"] == ResourceType.SharedService:
            return parse_obj_as(SharedService, resource)
        if resource["resourceType"] == ResourceType.Workspace:
            return parse_obj_as(Workspace, resource)
        if resource["resourceType"] == ResourceType.WorkspaceService:
            return parse_obj_as(WorkspaceService, resource)
        if resource["resourceType"] == ResourceType.UserResource:
            return parse_obj_as(UserResource, resource)

        return parse_obj_as(Resource, resource)

    def get_resource_by_template_name(self, template_name: str) -> Resource:
        query = f"SELECT TOP 1 * FROM c WHERE c.templateName = '{template_name}'"
        resources = self.query(query=query)
        if not resources:
            raise EntityDoesNotExist
        return parse_obj_as(Resource, resources[0])

    def validate_input_against_template(self, template_name: str, resource_input, resource_type: ResourceType, parent_template_name: str = "") -> ResourceTemplate:
        try:
            template = self._get_enriched_template(template_name, resource_type, parent_template_name)
        except EntityDoesNotExist:
            if resource_type == ResourceType.UserResource:
                raise ValueError(f'The template "{template_name}" does not exist or is not valid for the workspace service type "{parent_template_name}"')
            else:
                raise ValueError(f'The template "{template_name}" does not exist')

        self._validate_resource_parameters(resource_input.dict(), template)

        return parse_obj_as(ResourceTemplate, template)

    def patch_resource(self, resource: Resource, resource_patch: ResourcePatch, resource_template: ResourceTemplate, etag: str, resource_template_repo: ResourceTemplateRepository, user: User) -> Tuple[Resource, ResourceTemplate]:
        # create a deep copy of the resource to use for history, create the history item + add to history list
        resource_copy = copy.deepcopy(resource)
        history_item = ResourceHistoryItem(
            isEnabled=resource_copy.isEnabled,
            properties=resource_copy.properties,
            resourceVersion=resource_copy.resourceVersion,
            updatedWhen=resource_copy.updatedWhen,
            user=resource_copy.user
        )
        resource.history.append(history_item)

        # now update the resource props
        resource.resourceVersion = resource.resourceVersion + 1
        resource.user = user
        resource.updatedWhen = self.get_timestamp()

        if resource_patch.isEnabled is not None:
            resource.isEnabled = resource_patch.isEnabled

        if resource_patch.properties is not None and len(resource_patch.properties) > 0:
            self.validate_patch(resource_patch, resource_template_repo, resource_template)

            # if we're here then we're valid - update the props + persist
            resource.properties.update(resource_patch.properties)

        self.update_item_with_etag(resource, etag)
        return resource, resource_template

    def validate_patch(self, resource_patch: ResourcePatch, resource_template_repo: ResourceTemplateRepository, resource_template: ResourceTemplate):
        # get the enriched (combined) template
        enriched_template = resource_template_repo.enrich_template(resource_template, is_update=True)

        # validate the PATCH data against a cut down version of the full template.
        update_template = copy.deepcopy(enriched_template)
        update_template["required"] = []
        update_template["properties"] = {}
        for prop_name, prop in enriched_template["properties"].items():
            if("updateable" in prop.keys() and prop["updateable"] is True):
                update_template["properties"][prop_name] = prop

        self._validate_resource_parameters(resource_patch.dict(), update_template)

    def get_timestamp(self) -> float:
        return datetime.utcnow().timestamp()


# Cosmos query consts
IS_NOT_DELETED_CLAUSE = f'c.deploymentStatus != "{Status.Deleted}"'
IS_OPERATING_SHARED_SERVICE = f'c.deploymentStatus != "{Status.Deleted}" and c.deploymentStatus != "{Status.DeploymentFailed}"'
