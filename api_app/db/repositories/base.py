from typing import Optional
from azure.cosmos.aio import CosmosClient, ContainerProxy
from azure.cosmos import PartitionKey
from azure.core import MatchConditions
from pydantic import BaseModel

from core import config
from db.errors import UnableToAccessDatabase


class BaseRepository:
    @classmethod
    async def create(cls, client: CosmosClient, container_name: Optional[str] = None, partition_key: str = "/id"):
        partition_key_obj = PartitionKey(path=partition_key)
        cls._client: CosmosClient = client
        cls._container: ContainerProxy = await cls._get_container(container_name, partition_key_obj)
        return cls

    @property
    def container(self) -> ContainerProxy:
        return self._container

    @classmethod
    async def _get_container(cls, container_name, partition_key_obj) -> ContainerProxy:
        try:
            database = cls._client.get_database_client(config.STATE_STORE_DATABASE)
            container = await database.create_container_if_not_exists(id=container_name, partition_key=partition_key_obj)
            return container
        except Exception:
            raise UnableToAccessDatabase

    async def query(self, query: str, parameters: Optional[dict] = None):
        items = self.container.query_items(query=query, parameters=parameters)
        return [i async for i in items]

    async def read_item_by_id(self, item_id: str) -> dict:
        return await self.container.read_item(item=item_id, partition_key=item_id)

    async def save_item(self, item: BaseModel):
        await self.container.create_item(body=item.dict())

    async def update_item(self, item: BaseModel):
        await self.container.upsert_item(body=item.dict())

    async def update_item_with_etag(self, item: BaseModel, etag: str) -> BaseModel:
        await self.container.replace_item(item=item.id, body=item.dict(), etag=etag, match_condition=MatchConditions.IfNotModified)
        return await self.read_item_by_id(item.id)

    async def upsert_item_with_etag(self, item: BaseModel, etag: str) -> BaseModel:
        return await self.container.upsert_item(body=item.dict(), etag=etag, match_condition=MatchConditions.IfNotModified)

    async def update_item_dict(self, item_dict: dict):
        await self.container.upsert_item(body=item_dict)

    async def delete_item(self, item_id: str):
        await self.container.delete_item(item=item_id, partition_key=item_id)

    async def rename_field_name(self, old_field_name: str, new_field_name: str):
        for item in await self.query('SELECT * FROM c'):
            if old_field_name in item:
                item[new_field_name] = item[old_field_name]
                del item[old_field_name]
                await self.update_item_dict(item)
