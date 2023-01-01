from unittest.mock import AsyncMock
from mock import patch
import pytest
import pytest_asyncio

from db.repositories.resources_history import ResourceHistoryRepository
from models.domain.resource import Resource, NewResourceHistoryItem, ResourceType
from tests_ma.test_api.test_routes.test_resource_helpers import FAKE_CREATE_TIMESTAMP
from tests_ma.test_api.conftest import create_test_user

pytestmark = pytest.mark.asyncio

HISTORY_ID = "59676d53-5356-45b1-981a-180c0b089839"
RESOURCE_ID = "178c1ffe-de57-495b-b1eb-9bc37d3c5087"
USER_ID = "e5accc9a-3961-4da9-b5ee-1bc8a406388b"
RESOURCE_VERSION = 1
EXPECTED_QUERY = f'SELECT * FROM c WHERE c.resourceId = "{RESOURCE_ID}" AND c.resourceVersion = "{RESOURCE_VERSION}"'


@pytest_asyncio.fixture
async def resource_history_repo():
    with patch('db.repositories.base.BaseRepository._get_container', return_value=None):
        with patch('azure.cosmos.CosmosClient') as cosmos_client_mock:
            resource_history_repo = await ResourceHistoryRepository.create(cosmos_client_mock)
            yield resource_history_repo


@pytest.fixture
def sample_resource() -> Resource:
    return Resource(
        id=RESOURCE_ID,
        isEnabled=True,
        resourcePath="/resource/path",
        templateName="template_name",
        templateVersion="template_version",
        properties={
            'display_name': 'initial display name',
            'description': 'initial description',
            'computed_prop': 'computed_val'
        },
        resourceType=ResourceType.Workspace,
        etag="some-etag-value",
        resourceVersion=RESOURCE_VERSION,
        updatedWhen=FAKE_CREATE_TIMESTAMP,
        user=create_test_user()
    )


@pytest.fixture
def sample_resource_history() -> NewResourceHistoryItem:
    return NewResourceHistoryItem(
        id=HISTORY_ID,
        resourceId=RESOURCE_ID,
        isEnabled=True,
        resourceVersion=RESOURCE_VERSION,
        templateVersion="template_version",
        properties={
            'display_name': 'initial display name',
            'description': 'initial description',
            'computed_prop': 'computed_val'
        },
        updatedWhen=FAKE_CREATE_TIMESTAMP,
        user=create_test_user()
    )


@patch('db.repositories.resources_history.ResourceHistoryRepository.save_item', return_value=AsyncMock())
@patch('db.repositories.resources_history.ResourceHistoryRepository.query', return_value=[])
async def test_create_resource_history_item(mock_query, mock_save, resource_history_repo, sample_resource):

    resource_history = await resource_history_repo.create_resource_history_item(sample_resource)
    # Assertions
    assert isinstance(resource_history, NewResourceHistoryItem)
    mock_query.assert_called_once_with(EXPECTED_QUERY)
    mock_save.assert_called_once_with(resource_history)
    assert resource_history.id is not None
    assert resource_history.resourceId == sample_resource.id
    assert resource_history.isEnabled is True
    assert resource_history.properties == sample_resource.properties
    assert resource_history.resourceVersion == sample_resource.resourceVersion
    assert resource_history.updatedWhen == sample_resource.updatedWhen
    assert resource_history.user == sample_resource.user
    assert resource_history.templateVersion == sample_resource.templateVersion


@patch('db.repositories.resources_history.ResourceHistoryRepository.save_item', return_value=AsyncMock())
@patch('db.repositories.resources_history.ResourceHistoryRepository.query')
async def test_create_resource_history_item_when_history_item_already_exists(mock_query, mock_save, resource_history_repo, sample_resource):
    mock_query.return_value = [{"id": "existing-id"}]
    resource_history = await resource_history_repo.create_resource_history_item(sample_resource)

    assert not mock_save.called
    mock_query.assert_called_once_with(EXPECTED_QUERY)
    assert resource_history.id is not None
    assert resource_history.resourceId == sample_resource.id
    assert resource_history.isEnabled is True
    assert resource_history.properties == sample_resource.properties
    assert resource_history.resourceVersion == sample_resource.resourceVersion
    assert resource_history.updatedWhen == sample_resource.updatedWhen
    assert resource_history.user == sample_resource.user
    assert resource_history.templateVersion == sample_resource.templateVersion


@patch('db.repositories.resources_history.ResourceHistoryRepository.query')
async def test_get_resource_history_by_resource_id_if_found(mock_query, resource_history_repo, sample_resource_history):
    mock_query.return_value = [sample_resource_history]
    result = await resource_history_repo.get_resource_history_by_resource_id(RESOURCE_ID)

    assert result == mock_query.return_value


@patch('db.repositories.resources_history.ResourceHistoryRepository.query')
async def test_get_resource_history_by_resource_id_if_not_found(mock_query, resource_history_repo):
    mock_query.return_value = []
    result = await resource_history_repo.get_resource_history_by_resource_id(RESOURCE_ID)

    assert result == mock_query.return_value


def test_resource_history_query():
    # Call resource_history_query method
    result = ResourceHistoryRepository.resource_history_query("resource-id")

    assert result == 'SELECT * FROM c WHERE c.resourceId = "resource-id"'


def test_resource_history_with_resource_version_query():
    # Call resource_history_with_resource_version_query method
    result = ResourceHistoryRepository.resource_history_with_resource_version_query("resource-id", "1.0")

    assert result == 'SELECT * FROM c WHERE c.resourceId = "resource-id" AND c.resourceVersion = "1.0"'
