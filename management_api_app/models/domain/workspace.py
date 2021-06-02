from models.domain.resource import Resource, ResourceType


class Workspace(Resource):
    friendlyName: str
    description: str
    workspaceURL: str = ""
    resourceType = ResourceType.Workspace
