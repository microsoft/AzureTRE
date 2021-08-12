from mock import patch, MagicMock

from db.repositories.resources import ResourceRepository
from models.domain.resource import Deployment, Status, ResourceType, Resource


@patch('azure.cosmos.CosmosClient')
def test_save_resource_saves_the_items_to_the_database(cosmos_client_mock):
    resource_repo = ResourceRepository(cosmos_client_mock)
    resource_repo.container.create_item = MagicMock()
    resource = Resource(
        id="1234",
        resourceTemplateName="resource-type",
        resourceTemplateVersion="0.1.0",
        resourceTemplateParameters={},
        deployment=Deployment(status=Status.NotDeployed, message=""),
        resourceType=ResourceType.UserResource
    )

    resource_repo.save_resource(resource)

    resource_repo.container.create_item.assert_called_once_with(body=resource)
