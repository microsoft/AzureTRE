from models.domain.resource import ResourceType


class QueryBuilder:
    def __init__(self):
        self._where_clauses = []

    def select_active_resources(self, resource_type: ResourceType):
        active_resources = f'c.resourceType = "{resource_type.value}" AND c.isDeleted = false'
        self._where_clauses.append(active_resources)
        return self

    def with_id(self, resource_id: str):
        self._where_clauses.append(f'c.id = "{resource_id}"')
        return self

    def build(self) -> str:
        query = 'SELECT * FROM c'
        if self._where_clauses:
            query += ' WHERE '
        for clause in self._where_clauses:
            query += clause + ' AND '
        if self._where_clauses:
            # removes the final ' AND '
            query = query[:-5]
        return query
