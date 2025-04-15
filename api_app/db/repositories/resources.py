import copy
import semantic_version
from datetime import datetime
from typing import Optional, Tuple, List

from azure.cosmos.exceptions import CosmosResourceNotFoundError
from resources.strings import RESOURCE_ACTION_INSTALL
from core import config
from db.errors import VersionDowngradeDenied, EntityDoesNotExist, MajorVersionUpdateDenied, TargetTemplateVersionDoesNotExist, UserNotAuthorizedToUseTemplate
from db.repositories.resources_history import ResourceHistoryRepository
from db.repositories.base import BaseRepository
from db.repositories.resource_templates import ResourceTemplateRepository
from jsonschema import ValidationError, validate
from models.domain.authentication import User
from models.domain.resource import Resource, ResourceType
from models.domain.resource_template import ResourceTemplate
from models.domain.shared_service import SharedService
from models.domain.operation import Status
from models.domain.user_resource import UserResource
from models.domain.workspace import Workspace
from models.domain.workspace_service import WorkspaceService
from models.schemas.resource import ResourcePatch
from pydantic import UUID4, parse_obj_as


class ResourceRepository(BaseRepository):
    @classmethod
    async def create(cls):
        cls = ResourceRepository()
        await super().create(config.STATE_STORE_RESOURCES_CONTAINER)
        return cls

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

    async def _get_enriched_template(self, template_name: str, resource_type: ResourceType, parent_template_name: str = "") -> dict:
        template_repo = await ResourceTemplateRepository.create()
        template = await template_repo.get_current_template(template_name, resource_type, parent_template_name)
        return template_repo.enrich_template(template)

    @staticmethod
    def get_resource_base_spec_params():
        return {"tre_id": config.TRE_ID}

    async def get_resource_dict_by_id(self, resource_id: UUID4) -> dict:
        try:
            resource = await self.read_item_by_id(str(resource_id))
        except CosmosResourceNotFoundError:
            raise EntityDoesNotExist
        return resource

    async def get_resource_by_id(self, resource_id: UUID4) -> Resource:
        resource = await self.get_resource_dict_by_id(resource_id)

        if resource["resourceType"] == ResourceType.SharedService:
            return parse_obj_as(SharedService, resource)
        if resource["resourceType"] == ResourceType.Workspace:
            return parse_obj_as(Workspace, resource)
        if resource["resourceType"] == ResourceType.WorkspaceService:
            return parse_obj_as(WorkspaceService, resource)
        if resource["resourceType"] == ResourceType.UserResource:
            return parse_obj_as(UserResource, resource)

        return parse_obj_as(Resource, resource)

    async def get_active_resource_by_template_name(self, template_name: str) -> Resource:
        query = f"SELECT TOP 1 * FROM c WHERE c.templateName = '{template_name}' AND {IS_ACTIVE_RESOURCE}"
        resources = await self.query(query=query)
        if not resources:
            raise EntityDoesNotExist
        return parse_obj_as(Resource, resources[0])

    async def validate_input_against_template(self, template_name: str, resource_input, resource_type: ResourceType, user_roles: Optional[List[str]] = None, parent_template_name: Optional[str] = None) -> ResourceTemplate:
        try:
            template = await self._get_enriched_template(template_name, resource_type, parent_template_name)
        except EntityDoesNotExist:
            if resource_type == ResourceType.UserResource:
                raise ValueError(f'The template "{template_name}" does not exist or is not valid for the workspace service type "{parent_template_name}"')
            else:
                raise ValueError(f'The template "{template_name}" does not exist')

        # If authorizedRoles is empty, template is available to all users
        if "authorizedRoles" in template and template["authorizedRoles"]:
            # If authorizedRoles is not empty, the user is required to have at least one of authorizedRoles
            if len(set(template["authorizedRoles"]).intersection(set(user_roles))) == 0:
                raise UserNotAuthorizedToUseTemplate(f"User not authorized to use template {template_name}")

        self._validate_resource_parameters(resource_input.dict(), template)

        return parse_obj_as(ResourceTemplate, template)

    async def patch_resource(self, resource: Resource, resource_patch: ResourcePatch, resource_template: ResourceTemplate, etag: str, resource_template_repo: ResourceTemplateRepository, resource_history_repo: ResourceHistoryRepository, user: User, resource_action: str, force_version_update: bool = False) -> Tuple[Resource, ResourceTemplate]:
        await resource_history_repo.create_resource_history_item(resource)
        # now update the resource props
        resource.resourceVersion = resource.resourceVersion + 1
        resource.user = user
        resource.updatedWhen = self.get_timestamp()

        if resource_patch.isEnabled is not None:
            resource.isEnabled = resource_patch.isEnabled

        if resource_patch.templateVersion is not None:
            await self.validate_template_version_patch(resource, resource_patch, resource_template_repo, resource_template, force_version_update)
            resource.templateVersion = resource_patch.templateVersion

        if resource_patch.properties is not None and len(resource_patch.properties) > 0:
            self.validate_patch(resource_patch, resource_template_repo, resource_template, resource_action)

            # if we're here then we're valid - update the props + persist
            resource.properties.update(resource_patch.properties)

        await self.update_item_with_etag(resource, etag)
        return resource, resource_template

    async def get_resource_dependency_list(self, resource: Resource) -> List:
        # Get the parent resource path and id
        parent_resource_path = resource.resourcePath
        dependent_resources_list = []

        # Get all related resources
        related_resources_query = f"SELECT * FROM c WHERE CONTAINS(c.resourcePath, '{parent_resource_path}') AND c.deploymentStatus != '{Status.Deleted}'"
        related_resources = await self.query(query=related_resources_query)
        for resource in related_resources:
            resource_path = resource["resourcePath"]
            resource_level = resource_path.count("/")
            dependent_resources_list.append((resource, resource_level))
        # Sort resources list
        sorted_list = sorted(dependent_resources_list, key=lambda x: x[1], reverse=True)
        return [resource[0] for resource in sorted_list]

    async def validate_template_version_patch(self, resource: Resource, resource_patch: ResourcePatch, resource_template_repo: ResourceTemplateRepository, resource_template: ResourceTemplate, force_version_update: bool = False):
        parent_service_template_name = None
        if resource.resourceType == ResourceType.UserResource:
            try:
                resource_repo = await ResourceRepository.create()
                parent_service = await resource_repo.get_resource_by_id(resource.parentWorkspaceServiceId)
                parent_service_template_name = parent_service.templateName
            except EntityDoesNotExist:
                raise ValueError(f'Parent workspace service {resource.parentWorkspaceServiceId} not found')

        # validate Major upgrade
        try:
            desired_version = semantic_version.Version(resource_patch.templateVersion)
            current_version = semantic_version.Version(resource.templateVersion)
        except ValueError:
            raise ValidationError(f"Attempt to upgrade from {resource.templateVersion} to {resource_patch.templateVersion} denied. Invalid version format.")

        if not force_version_update:
            if desired_version.major > current_version.major:
                raise MajorVersionUpdateDenied(f'Attempt to upgrade from {current_version} to {desired_version} denied. major version upgrade is not allowed.')
            elif desired_version < current_version:
                raise VersionDowngradeDenied(f'Attempt to downgrade from {current_version} to {desired_version} denied. version downgrade is not allowed.')

        # validate if target template with desired version is registered
        try:
            await resource_template_repo.get_template_by_name_and_version(resource.templateName, resource_patch.templateVersion, resource_template.resourceType, parent_service_template_name)
        except EntityDoesNotExist:
            raise TargetTemplateVersionDoesNotExist(f"Template '{resource_template.name}' not found for resource type '{resource_template.resourceType}' with target template version '{resource_patch.templateVersion}'")

    def validate_patch(self, resource_patch: ResourcePatch, resource_template_repo: ResourceTemplateRepository, resource_template: ResourceTemplate, resource_action: str):
        # get the enriched (combined) template
        enriched_template = resource_template_repo.enrich_template(resource_template, is_update=True)

        # validate the PATCH data against a cut down version of the full template.
        update_template = copy.deepcopy(enriched_template)
        update_template["required"] = []
        update_template["properties"] = {}
        for prop_name, prop in enriched_template["properties"].items():
            if (resource_action == RESOURCE_ACTION_INSTALL or prop.get("updateable", False) is True):
                update_template["properties"][prop_name] = prop

        self._validate_resource_parameters(resource_patch.dict(), update_template)

    def get_timestamp(self) -> float:
        return datetime.utcnow().timestamp()


# Cosmos query consts
IS_NOT_DELETED_CLAUSE = f'c.deploymentStatus != "{Status.Deleted}"'
IS_ACTIVE_RESOURCE = f'c.deploymentStatus != "{Status.Deleted}" and c.deploymentStatus != "{Status.DeploymentFailed}"'
