from models.domain.resource import Resource, ResourceType


class Workspace(Resource):
    workspaceURL: str = ""
    resourceType = ResourceType.Workspace
