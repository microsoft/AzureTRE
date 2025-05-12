from db.repositories.base import BaseRepository
from resources import strings
from datetime import datetime
from azure.cosmos.aio import CosmosClient
from models.schemas.airlockprocess_status import AirlockStatus
from core import config
from pydantic import parse_obj_as

class AirlockStatusRepository(BaseRepository):
    @classmethod
    async def create(cls, client: CosmosClient):
        cls = AirlockStatusRepository()
        await super().create(client, config.STATE_STORE_AIRLOCK_STATUS)
        return cls


    @staticmethod
    def get_resource_base_spec_params():
        return {"tre_id": config.TRE_ID}

    def get_timestamp(self) -> float:
        return datetime.utcnow().timestamp()


    async def set_status(self, status_data:AirlockStatus):
        airlockstatus= AirlockStatus(
            status=status_data.status,
            message=status_data.message)
        await self.update_item(airlockstatus)
        return airlockstatus

    def get_status(self):
        query='SELECT * FROM c'
        data=self.query(query=query)
        return parse_obj_as(data,AirlockStatus)



