from models.domain.resource import ResourceType
from db.query_builder import QueryBuilder


def test_query_builder_with_no_where_clauses_select_all() -> None:
    expected_query = 'SELECT * FROM c'
    actual_query = QueryBuilder().build()
    assert expected_query == actual_query


def test_query_builder_selecting_active_resources() -> None:
    expected_query = 'SELECT * FROM c WHERE c.resourceType = "workspace" AND c.isDeleted = false'
    actual_query = QueryBuilder().select_active_resources(ResourceType.Workspace).build()
    assert expected_query == actual_query


def test_query_builder_selecting_active_resources_with_id() -> None:
    expected_query = 'SELECT * FROM c WHERE c.resourceType = "workspace" AND c.isDeleted = false AND c.id = "some_id"'
    actual_query = QueryBuilder().select_active_resources(ResourceType.Workspace).with_id("some_id").build()
    assert expected_query == actual_query
