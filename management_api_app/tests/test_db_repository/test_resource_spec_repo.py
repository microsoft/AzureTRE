import db.repositories.resource_specs
from unittest.mock import patch, MagicMock


@patch('azure.cosmos.CosmosClient')
def test_get_by_name_exisiting_document_returns_document(cosmos_client):
    sut = db.repositories.resource_specs.ResourceSpecRepository(cosmos_client)
    sut.container.query_items = MagicMock()
    sut.get_by_name(name="test")

    expected = "SELECT * FROM ResourceSpecs rs where rs.name = test"
    sut.container.query_items.assert_called_once_with(query=expected, enable_cross_partition_query=True)


@patch('azure.cosmos.CosmosClient')
def test_get_by_name_lastest_document_retuns_latest(cosmos_client):
    sut = db.repositories.resource_specs.ResourceSpecRepository(cosmos_client)
    sut.container.query_items = MagicMock(return_value="1")
    sut.get_latest(name="test")

    expected = "SELECT * FROM ResourceSpecs rs where rs.name = test AND rs.latest = true"
    sut.container.query_items.assert_called_once_with(query=expected, enable_cross_partition_query=True)


@patch('azure.cosmos.CosmosClient')
def test_get_by_name_and_version_returns_one_document(cosmos_client):
    sut = db.repositories.resource_specs.ResourceSpecRepository(cosmos_client)
    sut.container.query_items = MagicMock(return_value="1")
    sut.get_by_name_and_version(name="test", version="test")

    expected = "SELECT * FROM ResourceSpecs rs where rs.name = test AND rs.version = test"
    sut.container.query_items.assert_called_once_with(query=expected, enable_cross_partition_query=True)
