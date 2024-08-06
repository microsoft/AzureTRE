import pytest
import pytest_asyncio
from mock import patch
from models.domain.user_resource_template import UserResourceTemplate

from db.repositories.resource_templates import ResourceTemplateRepository
from db.errors import EntityDoesNotExist, InvalidInput
from models.domain.resource import ResourceType
from models.domain.resource_template import ResourceTemplate
from models.schemas.workspace_template import WorkspaceTemplateInCreate


pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def resource_template_repo():
    with patch('api.dependencies.database.Database.get_container_proxy', return_value=None):
        resource_template_repo = await ResourceTemplateRepository().create()
        yield resource_template_repo


def sample_resource_template_as_dict(name: str, version: str = "1.0", resource_type: ResourceType = ResourceType.Workspace) -> ResourceTemplate:
    return ResourceTemplate(
        id="a7a7a7bd-7f4e-4a4e-b970-dc86a6b31dfb",
        name=name,
        description="test",
        version=version,
        resourceType=resource_type,
        current=False,
        properties={},
        customActions=[],
        required=[]
    ).dict()


@patch('db.repositories.resource_templates.ResourceTemplateRepository.save_item')
@patch('uuid.uuid4')
async def test_create_workspace_template_succeeds_without_required(uuid_mock, save_item_mock, resource_template_repo):
    uuid_mock.return_value = "1234"
    expected_type = ResourceType.Workspace
    input_workspace_template = WorkspaceTemplateInCreate(
        name="my-tre-workspace",
        version="0.0.1",
        current=True,
        json_schema={
            "title": "My Workspace Template",
            "description": "This is a test workspace template schema.",
            "properties": {
                "updateable_property": {
                    "type": "string",
                    "title": "Test updateable property",
                    "updateable": True,
                },
            },
        },
        customActions=[],
    )
    returned_template = await resource_template_repo.create_template(input_workspace_template, expected_type)
    expected_resource_template = ResourceTemplate(
        id="1234",
        name=input_workspace_template.name,
        title=input_workspace_template.json_schema["title"],
        description=input_workspace_template.json_schema["description"],
        version=input_workspace_template.version,
        resourceType=expected_type,
        properties=input_workspace_template.json_schema["properties"],
        customActions=input_workspace_template.customActions,
        required=[],
        authorizedRoles=[],
        current=input_workspace_template.current
    )
    save_item_mock.assert_called_once_with(expected_resource_template)
    assert expected_resource_template == returned_template


@patch('db.repositories.resource_templates.ResourceTemplateRepository.query')
async def test_get_by_name_and_version_queries_db(query_mock, resource_template_repo):
    expected_query = 'SELECT * FROM c WHERE c.resourceType = "workspace" AND c.name = "test" AND c.version = "1.0"'
    query_mock.return_value = [sample_resource_template_as_dict(name="test", version="1.0")]

    await resource_template_repo.get_template_by_name_and_version(name="test", version="1.0", resource_type=ResourceType.Workspace)

    query_mock.assert_called_once_with(query=expected_query)


@patch('db.repositories.resource_templates.ResourceTemplateRepository.query')
async def test_get_by_name_and_version_returns_matching_template(query_mock, resource_template_repo):
    template_name = "test"
    template_version = "1.0"
    workspace_templates_in_db = [sample_resource_template_as_dict(name=template_name, version=template_version)]
    query_mock.return_value = workspace_templates_in_db

    template = await resource_template_repo.get_template_by_name_and_version(name=template_name, version=template_version, resource_type=ResourceType.Workspace)

    assert template.name == template_name


@patch('db.repositories.resource_templates.ResourceTemplateRepository.query')
async def test_get_by_name_and_version_raises_entity_does_not_exist_if_no_template_found(query_mock, resource_template_repo):
    template_name = "test"
    template_version = "1.0"
    query_mock.return_value = []

    with pytest.raises(EntityDoesNotExist):
        await resource_template_repo.get_template_by_name_and_version(name=template_name, version=template_version, resource_type=ResourceType.Workspace)


@patch('db.repositories.resource_templates.ResourceTemplateRepository.query')
async def test_get_current_by_name_queries_db(query_mock, resource_template_repo):
    template_name = "template1"
    expected_query = 'SELECT * FROM c WHERE c.resourceType = "workspace" AND c.name = "template1" AND c.current = true'
    query_mock.return_value = [sample_resource_template_as_dict(name="test")]

    await resource_template_repo.get_current_template(template_name=template_name, resource_type=ResourceType.Workspace)

    query_mock.assert_called_once_with(query=expected_query)


@patch('db.repositories.resource_templates.ResourceTemplateRepository.query')
async def test_get_current_by_name_returns_matching_template(query_mock, resource_template_repo):
    template_name = "template1"
    query_mock.return_value = [sample_resource_template_as_dict(name=template_name)]

    template = await resource_template_repo.get_current_template(template_name=template_name, resource_type=ResourceType.Workspace)

    assert template.name == template_name


@patch('db.repositories.resource_templates.ResourceTemplateRepository.query')
async def test_get_current_by_name_raises_entity_does_not_exist_if_no_template_found(query_mock, resource_template_repo):
    query_mock.return_value = []

    with pytest.raises(EntityDoesNotExist):
        await resource_template_repo.get_current_template(template_name="template1", resource_type=ResourceType.Workspace)


@patch('db.repositories.resource_templates.ResourceTemplateRepository.query')
async def test_get_templates_information_returns_unique_template_names(query_mock, resource_template_repo):
    query_mock.return_value = [
        {"name": "template1", "title": "title1", "description": "description1"},
        {"name": "template2", "title": "title2", "description": "description2"}
    ]

    result = await resource_template_repo.get_templates_information(ResourceType.Workspace)

    assert len(result) == 2
    assert result[0].name == "template1"
    assert result[1].name == "template2"


@patch('db.repositories.resource_templates.ResourceTemplateRepository.query')
async def test_get_templates_information_returns_only_templates_user_can_access(query_mock, resource_template_repo):
    query_mock.return_value = [
        # Will get filtered out as don't have admin role
        {"name": "template1", "title": "title1", "description": "description1", "authorizedRoles": ["admin"]},
        # Will get included as authorizedRoles=[] means any role is accepted
        {"name": "template2", "title": "title2", "description": "description2", "authorizedRoles": []},
        # Will get included as have test role
        {"name": "template3", "title": "title3", "description": "description3", "authorizedRoles": ["test"]}
    ]

    result = await resource_template_repo.get_templates_information(ResourceType.Workspace, ["test"])

    assert len(result) == 2
    assert result[0].name == "template2"
    assert result[1].name == "template3"


@patch('db.repositories.resource_templates.ResourceTemplateRepository.save_item')
@patch('uuid.uuid4')
async def test_create_workspace_template_item_calls_create_item_with_the_correct_parameters(uuid_mock, save_item_mock, resource_template_repo, input_workspace_template):
    uuid_mock.return_value = "1234"

    returned_template = await resource_template_repo.create_template(input_workspace_template, ResourceType.Workspace)

    expected_resource_template = ResourceTemplate(
        id="1234",
        name=input_workspace_template.name,
        title=input_workspace_template.json_schema["title"],
        description=input_workspace_template.json_schema["description"],
        version=input_workspace_template.version,
        resourceType=ResourceType.Workspace,
        properties=input_workspace_template.json_schema["properties"],
        allOf=input_workspace_template.json_schema["allOf"],
        customActions=input_workspace_template.customActions,
        required=input_workspace_template.json_schema["required"],
        current=input_workspace_template.current
    )
    save_item_mock.assert_called_once_with(expected_resource_template)
    assert expected_resource_template == returned_template


@patch('db.repositories.resource_templates.ResourceTemplateRepository.save_item')
@patch('uuid.uuid4')
async def test_create_item_created_with_the_expected_type(uuid_mock, save_item_mock, resource_template_repo, input_workspace_template):
    uuid_mock.return_value = "1234"
    expected_type = ResourceType.WorkspaceService
    returned_template = await resource_template_repo.create_template(input_workspace_template, expected_type)
    expected_resource_template = ResourceTemplate(
        id="1234",
        name=input_workspace_template.name,
        title=input_workspace_template.json_schema["title"],
        description=input_workspace_template.json_schema["description"],
        version=input_workspace_template.version,
        resourceType=expected_type,
        properties=input_workspace_template.json_schema["properties"],
        allOf=input_workspace_template.json_schema["allOf"],
        customActions=input_workspace_template.customActions,
        required=input_workspace_template.json_schema["required"],
        current=input_workspace_template.current
    )
    save_item_mock.assert_called_once_with(expected_resource_template)
    assert expected_resource_template == returned_template


@patch('db.repositories.resource_templates.ResourceTemplateRepository.save_item')
@patch('uuid.uuid4')
async def test_create_item_with_pipeline_succeeds(uuid_mock, save_item_mock, resource_template_repo, input_user_resource_template):
    uuid_mock.return_value = "1234"
    expected_type = ResourceType.UserResource
    # add the pipeline block
    pipeline = {
        "upgrade": [],
        "install": [],
        "uninstall": []
    }
    input_user_resource_template.json_schema["pipeline"] = pipeline
    returned_template = await resource_template_repo.create_template(input_user_resource_template, expected_type)
    expected_resource_template = UserResourceTemplate(
        id="1234",
        name=input_user_resource_template.name,
        title=input_user_resource_template.json_schema["title"],
        description=input_user_resource_template.json_schema["description"],
        version=input_user_resource_template.version,
        resourceType=expected_type,
        properties=input_user_resource_template.json_schema["properties"],
        customActions=input_user_resource_template.customActions,
        required=input_user_resource_template.json_schema["required"],
        current=input_user_resource_template.current,
        pipeline=pipeline,
        parentWorkspaceService=""
    )
    save_item_mock.assert_called_once_with(expected_resource_template)
    assert expected_resource_template == returned_template


@pytest.mark.parametrize(
    "pipeline",
    [
        {
            "install": [{"stepId": "1"}, {"stepId": "1"}],
            "upgrade": [{"stepId": "main"}, {"stepId": "2"}],
        },
        {
            "install": [{"stepId": "main"}, {"stepId": "1"}],
            "upgrade": [{"stepId": "main"}, {"stepId": "1"}],
        },
        {
            "install": [{"stepId": "main"}, {"stepId": "1"}],
            "upgrade": [{"stepId": "main"}, {"stepId": "main"}],
        },
    ],
)
async def test_create_template_with_pipeline_that_has_duplicated_step_id_fails_with_invalid_input_error(resource_template_repo, input_user_resource_template, pipeline):
    input_user_resource_template.json_schema["pipeline"] = pipeline
    with pytest.raises(InvalidInput):
        await resource_template_repo.create_template(input_user_resource_template, ResourceType.UserResource)


@patch('db.repositories.resource_templates.ResourceTemplateRepository.save_item')
async def test_create_template_with_pipeline_without_duplicated_step_id_succeeds(_, resource_template_repo, input_user_resource_template):
    input_user_resource_template.json_schema["pipeline"] = {
        "install": [{"stepId": "main"}, {"stepId": "1"}],
        "upgrade": [{"stepId": "main"}, {"stepId": "2"}],
    }

    created = await resource_template_repo.create_template(input_user_resource_template, ResourceType.UserResource)
    assert created.pipeline


@patch('db.repositories.resource_templates.ResourceTemplateRepository.save_item')
async def test_create_template_with_null_pipeline_creates_template_without_pipeline(_, resource_template_repo, input_user_resource_template):
    input_user_resource_template.json_schema["pipeline"] = None
    created = await resource_template_repo.create_template(input_user_resource_template, ResourceType.UserResource)
    assert created.pipeline is None
