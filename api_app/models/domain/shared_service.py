from models.domain.resource import Resource, ResourceType


class SharedService(Resource):
    """
    Shared service request
    """
    resourceType: ResourceType = ResourceType.SharedService
