from azure.cosmos import ContainerProxy, CosmosClient, PartitionKey

from core import config
from db.errors import UnableToAccessDatabase


class BaseRepository:
    def __init__(self, client: CosmosClient, container_name: str = None) -> None:
        self._client: CosmosClient = client
        self._container: ContainerProxy = self.get_container(container_name)

    @property
    def container(self) -> ContainerProxy:
        return self._container

    def get_container(self, container_name) -> ContainerProxy:
        try:
            database = self._client.get_database_client(config.STATE_STORE_DATABASE)
            return database.create_container_if_not_exists(id=container_name, partition_key=PartitionKey(path="/appId"))
        except Exception:
            raise UnableToAccessDatabase
