import uuid

from azure.cosmos import CosmosClient

from db.errors import EntityDoesNotExist
from db.repositories.resource_templates import ResourceTemplateRepository
from db.repositories.resources import ResourceRepository

from models.domain.resource import ResourceType, Status, Deployment
from models.domain.resource_template import ResourceTemplate
from models.domain.user_resource import UserResource
from models.schemas.user_resource import UserResourceInCreate
from resources import strings
from services.concatjsonschema import enrich_workspace_service_schema_defs


class UserResourceRepository(ResourceRepository):
    def __init__(self, client: CosmosClient):
        super().__init__(client)

    @staticmethod
    def _active_workspaces_query():
        return f'SELECT * FROM c WHERE c.resourceType = {ResourceType.UserResource} AND c.deleted = false'

    def _get_current_user_resource_template(self, template_name) -> ResourceTemplate:
        resource_template_repo = ResourceTemplateRepository(self._client)
        template = resource_template_repo.get_current_resource_template_by_name(template_name,
                                                                                ResourceType.UserResource)
        return enrich_workspace_service_schema_defs(template)

    def create_user_resource_item(self, user_resource_create: UserResourceInCreate,
                                  workspace_id: str, parent_workspace_service_id: str) -> UserResource:
        full_workspace_service_id = str(uuid.uuid4())

        try:
            current_template = self._get_current_user_resource_template(
                user_resource_create.userResourceType)
            template_version = current_template["version"]
        except EntityDoesNotExist:
            raise ValueError(
                f"The user resource type '{user_resource_create.userResourceType}' does not exist")

        self._validate_resource_parameters(user_resource_create.dict(), current_template)

        user_resource = UserResource(
            id=full_workspace_service_id,
            workspaceId=workspace_id,
            parentWorkspaceServiceId=parent_workspace_service_id,
            displayName=user_resource_create.properties["display_name"],
            description=user_resource_create.properties["description"],
            resourceTemplateName=user_resource_create.userResourceType,
            resourceTemplateVersion=template_version,
            resourceTemplateParameters=user_resource_create.properties,
            deployment=Deployment(status=Status.NotDeployed, message=strings.RESOURCE_STATUS_NOT_DEPLOYED_MESSAGE)
        )

        return user_resource
