from typing import Optional
from azure.cosmos.aio import ContainerProxy
from azure.core import MatchConditions
from pydantic import BaseModel

from api.dependencies.database import Database
from db.errors import UnableToAccessDatabase


class BaseRepository:
    @classmethod
    async def create(cls, container_name: Optional[str] = None):
        try:
            cls._container: ContainerProxy = await Database().get_container_proxy(container_name)
        except Exception:
            raise UnableToAccessDatabase

        return cls

    @property
    def container(self) -> ContainerProxy:
        return self._container

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
