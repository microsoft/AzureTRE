from mock import patch
import pytest

from db.repositories.workspace_templates import WorkspaceTemplateRepository
from db.errors import EntityDoesNotExist
from models.domain.resource import ResourceType
from models.domain.resource_template import ResourceTemplate


def get_sample_workspace_template(name: str, version: str = "1.0") -> ResourceTemplate:
    return ResourceTemplate(
        id="a7a7a7bd-7f4e-4a4e-b970-dc86a6b31dfb",
        name=name,
        description="some description",
        version=version,
        resourceType=ResourceType.Workspace,
        parameters=[],
        current=False
    )


@patch('db.repositories.workspace_templates.WorkspaceTemplateRepository.query')
@patch('azure.cosmos.CosmosClient')
def test_get_by_name_queries_db(cosmos_client_mock, wt_query_mock):
    template_repo = WorkspaceTemplateRepository(cosmos_client_mock)
    expected_query = 'SELECT * FROM c WHERE c.resourceType = "workspace" AND c.name = "test"'

    template_repo.get_workspace_templates_by_name(name="test")

    wt_query_mock.assert_called_once_with(query=expected_query)


@patch('db.repositories.workspace_templates.WorkspaceTemplateRepository.query')
@patch('azure.cosmos.CosmosClient')
def test_get_by_name_returns_all_matching_templates(cosmos_client_mock, wt_query_mock):
    template_repo = WorkspaceTemplateRepository(cosmos_client_mock)
    template_name = "test"
    workspace_templates_in_db = [
        get_sample_workspace_template(name=template_name, version="0.1.0"),
        get_sample_workspace_template(name=template_name, version="0.2.0"),
    ]
    wt_query_mock.return_value = workspace_templates_in_db

    templates = template_repo.get_workspace_templates_by_name(name=template_name)

    assert len(templates) == len(workspace_templates_in_db)


@patch('db.repositories.workspace_templates.WorkspaceTemplateRepository.query')
@patch('azure.cosmos.CosmosClient')
def test_get_by_name_and_version_queries_db(cosmos_client_mock, wt_query_mock):
    template_repo = WorkspaceTemplateRepository(cosmos_client_mock)
    expected_query = 'SELECT * FROM c WHERE c.resourceType = "workspace" AND c.name = "test" AND c.version = "1.0"'
    wt_query_mock.return_value = [get_sample_workspace_template(name="test", version="1.0")]

    template_repo.get_workspace_template_by_name_and_version(name="test", version="1.0")

    wt_query_mock.assert_called_once_with(query=expected_query)


@patch('db.repositories.workspace_templates.WorkspaceTemplateRepository.query')
@patch('azure.cosmos.CosmosClient')
def test_get_by_name_and_version_returns_matching_template(cosmos_client_mock, wt_query_mock):
    template_repo = WorkspaceTemplateRepository(cosmos_client_mock)
    template_name = "test"
    template_version = "1.0"
    workspace_templates_in_db = [get_sample_workspace_template(name=template_name, version=template_version)]
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
    wt_query_mock.return_value = [get_sample_workspace_template(name="test", version="1.0")]

    template_repo.get_current_workspace_template_by_name(name="test")

    wt_query_mock.assert_called_once_with(query=expected_query)


@patch('db.repositories.workspace_templates.WorkspaceTemplateRepository.query')
@patch('azure.cosmos.CosmosClient')
def test_get_current_by_name_returns_matching_template(cosmos_client_mock, wt_query_mock):
    template_repo = WorkspaceTemplateRepository(cosmos_client_mock)
    template_name = "test"
    workspace_templates_in_db = [get_sample_workspace_template(name=template_name)]
    wt_query_mock.return_value = workspace_templates_in_db

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
