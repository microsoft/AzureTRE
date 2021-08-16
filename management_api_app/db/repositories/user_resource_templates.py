import uuid

from azure.cosmos import CosmosClient

from db.repositories.resource_templates import ResourceTemplateRepository
from models.domain.resource import ResourceType
from models.domain.user_resource_template import UserResourceTemplate
from models.schemas.user_resource_template import UserResourceTemplateInCreate


class UserResourceTemplateRepository(ResourceTemplateRepository):
    def __init__(self, client: CosmosClient):
        super().__init__(client)

    def create_user_resource_template_item(self, template_create: UserResourceTemplateInCreate, workspace_service_template_name: str) -> UserResourceTemplate:
        item_id = str(uuid.uuid4())
        description = template_create.json_schema["description"]
        required = template_create.json_schema["required"]
        properties = template_create.json_schema["properties"]
        resource_template = UserResourceTemplate(
            id=item_id,
            name=template_create.name,
            parentWorkspaceService=workspace_service_template_name,
            description=description,
            version=template_create.version,
            resourceType=ResourceType.UserResource,
            current=template_create.current,
            required=required,
            properties=properties
        )
        self.save_item(resource_template)
        return resource_template
