import uuid
from typing import List

from azure.cosmos import CosmosClient
from pydantic import parse_obj_as

from db.repositories.resources import ResourceRepository
from models.domain.resource import ResourceType, Status, Deployment
from models.domain.user_resource import UserResource
from models.schemas.user_resource import UserResourceInCreate
from resources import strings


class UserResourceRepository(ResourceRepository):
    def __init__(self, client: CosmosClient):
        super().__init__(client)

    @staticmethod
    def active_user_resources_query(service_id: str):
        return f'SELECT * FROM c WHERE c.resourceType = "{ResourceType.UserResource}" AND c.deployment.status != "{Status.Deleted}" AND c.parentWorkspaceServiceId = "{service_id}"'

    def create_user_resource_item(self, user_resource_input: UserResourceInCreate, workspace_id: str, parent_workspace_service_id: str, user_id: str) -> UserResource:
        full_user_resource_id = str(uuid.uuid4())

        template_version = self.validate_input_against_template(user_resource_input.userResourceType, user_resource_input, ResourceType.UserResource)

        # we don't want something in the input to overwrite the system parameters, so dict.update can't work.
        resource_spec_parameters = {**user_resource_input.properties, **self.get_user_resource_spec_params()}

        user_resource = UserResource(
            id=full_user_resource_id,
            workspaceId=workspace_id,
            ownerId=user_id,
            parentWorkspaceServiceId=parent_workspace_service_id,
            resourceTemplateName=user_resource_input.userResourceType,
            resourceTemplateVersion=template_version,
            resourceTemplateParameters=resource_spec_parameters,
            deployment=Deployment(status=Status.NotDeployed, message=strings.RESOURCE_STATUS_NOT_DEPLOYED_MESSAGE)
        )

        return user_resource

    def get_user_resources_for_workspace_service(self, service_id) -> List[UserResource]:
        """
        returns a list of "non-deleted" user resources linked to this workspace service
        """
        query = self.active_user_resources_query(service_id)
        user_resources = self.query(query=query)
        return parse_obj_as(List[UserResource], user_resources)

    def get_user_resource_by_id(self, resource_id: str) -> UserResource:
        user_resource = self.get_resource_dict_by_type_and_id(resource_id, ResourceType.UserResource)
        return parse_obj_as(UserResource, user_resource)

    def get_user_resource_spec_params(self):
        return self.get_resource_base_spec_params()
