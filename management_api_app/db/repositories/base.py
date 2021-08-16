from azure.cosmos import ContainerProxy, CosmosClient, PartitionKey
from pydantic import BaseModel

from core import config
from db.errors import UnableToAccessDatabase


class BaseRepository:
    def __init__(self, client: CosmosClient, container_name: str = None) -> None:
        self._client: CosmosClient = client
        self._container: ContainerProxy = self._get_container(container_name)

    @property
    def container(self) -> ContainerProxy:
        return self._container

    def _get_container(self, container_name) -> ContainerProxy:
        try:
            database = self._client.get_database_client(config.STATE_STORE_DATABASE)
            container = database.create_container_if_not_exists(id=container_name, partition_key=PartitionKey(path="/id"))
            properties = container.read()
            print(properties['partitionKey'])
            return container
        except Exception:
            raise UnableToAccessDatabase

    def query(self, query: str):
        return list(self.container.query_items(query=query, enable_cross_partition_query=True))

    def save_item(self, item: BaseModel):
        self.container.create_item(body=item.dict())

    def update_item(self, item: BaseModel):
        self.container.upsert_item(body=item.dict())

    def delete_item(self, item_id: str):
        self.container.delete_item(item=item_id, partition_key=item_id)
