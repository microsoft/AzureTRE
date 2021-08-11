from mock import patch

from db.repositories.user_resource_templates import UserResourceTemplateRepository
from models.domain.resource import ResourceType
from models.domain.user_resource_template import UserResourceTemplate


@patch('db.repositories.user_resource_templates.UserResourceTemplateRepository.create_item')
@patch('uuid.uuid4')
@patch('azure.cosmos.CosmosClient')
def test_create_workspace_template_item_calls_create_item_with_the_correct_parameters(cosmos_mock, uuid_mock, create_mock, input_user_resource_template):
    user_resource_template_repo = UserResourceTemplateRepository(cosmos_mock)
    uuid_mock.return_value = "1234"
    workspace_service_template_name = "guacamole"

    returned_template = user_resource_template_repo.create_user_resource_template_item(input_user_resource_template, workspace_service_template_name)

    expected_resource_template = UserResourceTemplate(
        id="1234",
        name=input_user_resource_template.name,
        parentWorkspaceService=workspace_service_template_name,
        description=input_user_resource_template.json_schema["description"],
        version=input_user_resource_template.version,
        resourceType=ResourceType.UserResource,
        properties=input_user_resource_template.json_schema["properties"],
        required=input_user_resource_template.json_schema["required"],
        current=input_user_resource_template.current
    )
    create_mock.assert_called_once_with(expected_resource_template)
    assert expected_resource_template == returned_template
