from pydantic import Field

from models.domain.resource import ResourceType
from models.domain.resource_template import ResourceTemplate


class UserResourceTemplate(ResourceTemplate):
    parentWorkspaceService: str = Field("", title="Parent Workspace Service", description="The parent workspace service under which services with this template can be created")
    resourceType: ResourceType = ResourceType.UserResource
