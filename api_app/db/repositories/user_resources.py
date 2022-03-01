import uuid
from typing import List

from azure.cosmos import CosmosClient
from pydantic import parse_obj_as

from db.errors import EntityDoesNotExist
from db.repositories.resource_templates import ResourceTemplateRepository
from db.repositories.resources import ResourceRepository, IS_ACTIVE_CLAUSE
from models.domain.resource import ResourceType
from models.domain.user_resource import UserResource
from models.schemas.resource import ResourcePatch
from models.schemas.user_resource import UserResourceInCreate


class UserResourceRepository(ResourceRepository):
    def __init__(self, client: CosmosClient):
        super().__init__(client)

    @staticmethod
    def user_resources_query(workspace_id: str, service_id: str):
        return f'SELECT * FROM c WHERE c.resourceType = "{ResourceType.UserResource}" AND c.parentWorkspaceServiceId = "{service_id}" AND c.workspaceId = "{workspace_id}"'

    @staticmethod
    def active_user_resources_query(workspace_id: str, service_id: str):
        return f'SELECT * FROM c WHERE {IS_ACTIVE_CLAUSE} AND c.resourceType = "{ResourceType.UserResource}" AND c.parentWorkspaceServiceId = "{service_id}" AND c.workspaceId = "{workspace_id}"'

    def create_user_resource_item(self, user_resource_input: UserResourceInCreate, workspace_id: str, parent_workspace_service_id: str, parent_template_name: str, user_id: str) -> UserResource:
        full_user_resource_id = str(uuid.uuid4())

        template_version = self.validate_input_against_template(user_resource_input.templateName, user_resource_input, ResourceType.UserResource, parent_template_name)

        # we don't want something in the input to overwrite the system parameters, so dict.update can't work.
        resource_spec_parameters = {**user_resource_input.properties, **self.get_user_resource_spec_params()}

        user_resource = UserResource(
            id=full_user_resource_id,
            workspaceId=workspace_id,
            ownerId=user_id,
            parentWorkspaceServiceId=parent_workspace_service_id,
            templateName=user_resource_input.templateName,
            templateVersion=template_version,
            properties=resource_spec_parameters,
            resourcePath=f'/workspaces/{workspace_id}/workspace-services/{parent_workspace_service_id}/user-resources/{full_user_resource_id}',
            etag=''
        )

        return user_resource

    def get_user_resources_for_workspace_service(self, workspace_id: str, service_id: str) -> List[UserResource]:
        """
        returns a list of "non-deleted" user resources linked to this workspace service
        """
        query = self.active_user_resources_query(workspace_id, service_id)
        user_resources = self.query(query=query)
        return parse_obj_as(List[UserResource], user_resources)

    def get_user_resource_by_id(self, workspace_id: str, service_id: str, resource_id: str) -> UserResource:
        query = self.user_resources_query(workspace_id, service_id) + f' AND c.id = "{resource_id}"'
        user_resources = self.query(query=query)
        if not user_resources:
            raise EntityDoesNotExist
        return parse_obj_as(UserResource, user_resources[0])

    def get_user_resource_spec_params(self):
        return self.get_resource_base_spec_params()

    def patch_user_resource(self, user_resource: UserResource, user_resource_patch: ResourcePatch, etag: str, resource_template_repo: ResourceTemplateRepository):
        # get user resource template
        user_resource_template = resource_template_repo.get_template_by_name_and_version(user_resource.templateName, user_resource.templateVersion, ResourceType.UserResource, parent_service_name=user_resource.parentWorkspaceServiceId)
        return self.patch_resource(user_resource, user_resource_patch, user_resource_template, etag)
