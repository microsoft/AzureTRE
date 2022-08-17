from azure.cosmos import ContainerProxy, CosmosClient, PartitionKey
from azure.core import MatchConditions
from pydantic import BaseModel

from core import config
from db.errors import UnableToAccessDatabase


PARTITION_KEY = PartitionKey(path="/id")


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
            container = database.create_container_if_not_exists(id=container_name, partition_key=PARTITION_KEY)
            properties = container.read()
            print(properties['partitionKey'])
            return container
        except Exception:
            raise UnableToAccessDatabase

    def query(self, query: str, parameters: dict = None):
        return list(self.container.query_items(query=query, parameters=parameters, enable_cross_partition_query=True))

    def read_item_by_id(self, item_id: str) -> dict:
        return self.container.read_item(item=item_id, partition_key=item_id)

    def save_item(self, item: BaseModel):
        self.container.create_item(body=item.dict())

    def update_item(self, item: BaseModel):
        self.container.upsert_item(body=item.dict())

    def update_item_with_etag(self, item: BaseModel, etag: str) -> BaseModel:
        self.container.replace_item(item=item.id, body=item.dict(), etag=etag, match_condition=MatchConditions.IfNotModified)
        return self.read_item_by_id(item.id)

    def update_item_dict(self, item_dict: dict):
        self.container.upsert_item(body=item_dict)

    def delete_item(self, item_id: str):
        self.container.delete_item(item=item_id, partition_key=item_id)

    def rename_field_name(self, old_field_name: str, new_field_name: str):
        for item in self.query('SELECT * FROM c'):
            if old_field_name in item:
                item[new_field_name] = item[old_field_name]
                del item[old_field_name]
                self.update_item_dict(item)
