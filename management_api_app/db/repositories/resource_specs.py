from typing import List

from azure.cosmos import ContainerProxy, CosmosClient

from models.domain.resource import ResourceSpec
from db.repositories.base import BaseRepository
from core.config import STATE_STORE_RESOURCE_SPECS_CONTAINER


class ResourceSpecRepository(BaseRepository):
    def __init__(self, client: CosmosClient):
        super().__init__(client, STATE_STORE_RESOURCE_SPECS_CONTAINER)

    @property
    def container(self) -> ContainerProxy:
        return self._container

    def _query(self, query: str):
        resource_specs = list(self.container.query_items(query=query, enable_cross_partition_query=True))
        return resource_specs

    def get_by_name(self, name: str, latest=False) -> List[ResourceSpec]:
        by_name = f"SELECT * FROM ResourceSpecs rs where rs.name = {name}"
        if latest:
            by_name += " AND rs.latest = true"
        return self._query(by_name)

    def get_by_name_and_version(self, name: str, version: str) -> ResourceSpec:
        by_name_and_version = f"SELECT * FROM ResourceSpecs rs where rs.name = {name} AND rs.version = {version}"
        specs = self._query(by_name_and_version)
        assert(len(specs) == 1)  # name and version should have been unique
        return specs[0]

    def get_latest(self, name: str) -> ResourceSpec:
        specs = self.get_by_name(name, latest=True)
        assert(len(specs) == 1)  # Only one latest allowed.
        return specs[0]
