import pytest
from mock import MagicMock, patch

from db.repositories.workspace_templates import WorkspaceTemplateRepository
from db.errors import EntityDoesNotExist
from models.domain.resource import ResourceType
from models.domain.resource_template import ResourceTemplate
from models.schemas.workspace_template import WorkspaceTemplateInCreate


def sample_workspace_template(name: str, version: str = "1.0") -> ResourceTemplate:
    return ResourceTemplate(
        id="a7a7a7bd-7f4e-4a4e-b970-dc86a6b31dfb",
        name=name,
        description="some description",
        version=version,
        resourceType=ResourceType.Workspace,
        parameters=[],
        current=False
    )


def sample_workspace_template_as_dict(name: str, version: str = "1.0") -> dict:
    return sample_workspace_template(name, version).dict()


@patch('db.repositories.workspace_templates.WorkspaceTemplateRepository.query')
@patch('azure.cosmos.CosmosClient')
def test_get_by_name_queries_db(cosmos_client_mock, wt_query_mock):
    template_repo = WorkspaceTemplateRepository(cosmos_client_mock)
    expected_query = 'SELECT * FROM c WHERE c.resourceType = "workspace" AND c.name = "test"'
    wt_query_mock.return_value = [sample_workspace_template_as_dict(name="test")]

    template_repo.get_workspace_templates_by_name(name="test")

    wt_query_mock.assert_called_once_with(query=expected_query)


@patch('db.repositories.workspace_templates.WorkspaceTemplateRepository.query')
@patch('azure.cosmos.CosmosClient')
def test_get_by_name_returns_all_matching_templates(cosmos_client_mock, wt_query_mock):
    template_repo = WorkspaceTemplateRepository(cosmos_client_mock)
    template_name = "test"
    workspace_templates_in_db = [
        sample_workspace_template_as_dict(name=template_name, version="0.1.0"),
        sample_workspace_template_as_dict(name=template_name, version="0.2.0"),
    ]
    wt_query_mock.return_value = workspace_templates_in_db

    templates = template_repo.get_workspace_templates_by_name(name=template_name)

    assert len(templates) == len(workspace_templates_in_db)


@patch('db.repositories.workspace_templates.WorkspaceTemplateRepository.query')
@patch('azure.cosmos.CosmosClient')
def test_get_by_name_and_version_queries_db(cosmos_client_mock, wt_query_mock):
    template_repo = WorkspaceTemplateRepository(cosmos_client_mock)
    expected_query = 'SELECT * FROM c WHERE c.resourceType = "workspace" AND c.name = "test" AND c.version = "1.0"'
    wt_query_mock.return_value = [sample_workspace_template_as_dict(name="test", version="1.0")]

    template_repo.get_workspace_template_by_name_and_version(name="test", version="1.0")

    wt_query_mock.assert_called_once_with(query=expected_query)


@patch('db.repositories.workspace_templates.WorkspaceTemplateRepository.query')
@patch('azure.cosmos.CosmosClient')
def test_get_by_name_and_version_returns_matching_template(cosmos_client_mock, wt_query_mock):
    template_repo = WorkspaceTemplateRepository(cosmos_client_mock)
    template_name = "test"
    template_version = "1.0"
    workspace_templates_in_db = [sample_workspace_template_as_dict(name=template_name, version=template_version)]
    wt_query_mock.return_value = workspace_templates_in_db

    template = template_repo.get_workspace_template_by_name_and_version(name=template_name, version=template_version)

    assert template.name == template_name


@patch('db.repositories.workspace_templates.WorkspaceTemplateRepository.query')
@patch('azure.cosmos.CosmosClient')
def test_get_by_name_and_version_raises_entity_does_not_exist_if_no_template_found(cosmos_client_mock, wt_query_mock):
    template_repo = WorkspaceTemplateRepository(cosmos_client_mock)
    template_name = "test"
    template_version = "1.0"
    wt_query_mock.return_value = []

    with pytest.raises(EntityDoesNotExist):
        template_repo.get_workspace_template_by_name_and_version(name=template_name, version=template_version)


@patch('db.repositories.workspace_templates.WorkspaceTemplateRepository.query')
@patch('azure.cosmos.CosmosClient')
def test_get_current_by_name_queries_db(cosmos_client_mock, wt_query_mock):
    template_repo = WorkspaceTemplateRepository(cosmos_client_mock)
    expected_query = 'SELECT * FROM c WHERE c.resourceType = "workspace" AND c.name = "test" AND c.current = true'
    wt_query_mock.return_value = [sample_workspace_template_as_dict(name="test")]

    template_repo.get_current_workspace_template_by_name(name="test")

    wt_query_mock.assert_called_once_with(query=expected_query)


@patch('db.repositories.workspace_templates.WorkspaceTemplateRepository.query')
@patch('azure.cosmos.CosmosClient')
def test_get_current_by_name_returns_matching_template(cosmos_client_mock, wt_query_mock):
    template_repo = WorkspaceTemplateRepository(cosmos_client_mock)
    template_name = "test"
    wt_query_mock.return_value = [sample_workspace_template_as_dict(name=template_name)]

    template = template_repo.get_current_workspace_template_by_name(name=template_name)

    assert template.name == template_name


@patch('db.repositories.workspace_templates.WorkspaceTemplateRepository.query')
@patch('azure.cosmos.CosmosClient')
def test_get_current_by_name_raises_entity_does_not_exist_if_no_template_found(cosmos_client_mock, wt_query_mock):
    template_repo = WorkspaceTemplateRepository(cosmos_client_mock)
    wt_query_mock.return_value = []

    with pytest.raises(EntityDoesNotExist):
        template_repo.get_current_workspace_template_by_name(name="test")


@patch('db.repositories.workspace_templates.WorkspaceTemplateRepository.query')
@patch('azure.cosmos.CosmosClient')
def test_get_workspace_template_names_returns_unique_template_names(cosmos_client_mock, wt_query_mock):
    template_repo = WorkspaceTemplateRepository(cosmos_client_mock)
    wt_query_mock.return_value = [
        {"name": "template1"},
        {"name": "template1"},
        {"name": "template2"}
    ]

    template_names = template_repo.get_workspace_template_names()
    assert len(template_names) == 2
    assert "template1" in template_names
    assert "template2" in template_names


@patch('db.repositories.workspace_templates.WorkspaceTemplateRepository.create_item')
@patch('uuid.uuid4')
@patch('azure.cosmos.CosmosClient')
def test_create_item(cosmos_mock, uuid_mock, create_mock):
    template_repo = WorkspaceTemplateRepository(cosmos_mock)
    uuid_mock.return_value = "1234"
    payload = WorkspaceTemplateInCreate(
        name="name",
        description="some description",
        version="0.0.1",
        parameters=[],
        current=False
    )
    returned_template = template_repo.create_workspace_template_item(payload)
    expected_resource_template = ResourceTemplate(
        id="1234",
        name="name",
        description="some description",
        version="0.0.1",
        resourceType=ResourceType.Workspace,
        parameters=[],
        current=False
    )
    create_mock.assert_called_once_with(expected_resource_template)
    assert expected_resource_template == returned_template


@patch('db.repositories.workspace_templates.WorkspaceTemplateRepository.container')
@patch('azure.cosmos.CosmosClient')
def test_updating_an_item(cosmos_mock, container_mock):
    container_mock.upsert_item = MagicMock()
    template_repo = WorkspaceTemplateRepository(cosmos_mock)
    resource_template = sample_workspace_template("blah", "blah")
    template_repo.update_item(resource_template)

    container_mock.upsert_item.assert_called_once_with(resource_template.dict())
