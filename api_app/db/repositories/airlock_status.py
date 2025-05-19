import uuid
from db.repositories.base import BaseRepository

from datetime import datetime
from azure.cosmos.aio import CosmosClient
from models.domain.authentication import User
from models.domain.airlockstatus import AirLockStatus
from models.schemas.airlockprocess_status import AirlockProcessStatus
from core import config
from pydantic import parse_obj_as

class AirlockStatusRepository(BaseRepository):
    @classmethod
    async def create(cls, client: CosmosClient):
        cls = AirlockStatusRepository()
        await super().create(client, config.STATE_STORE_AIRLOCK_STATUS)
        return cls

    async def set_status(self, status_data: AirlockProcessStatus, user) -> AirLockStatus:

        airlock_status = await self.get_status()
        if airlock_status:
            airlock_status.status = status_data.status
            airlock_status.message = status_data.message
            airlock_status.updatedBy = user
            airlock_status.updatedWhen = datetime.utcnow().timestamp()
        else:
            airlock_status = AirLockStatus(
                id= str(uuid.uuid4()),
                status=status_data.status,
                message=status_data.message,
                createdBy=user,
                createdWhen=datetime.utcnow().timestamp(),
                updatedBy=user,
                updatedWhen=datetime.utcnow().timestamp())
        await self.update_item(airlock_status)
        return airlock_status


    async def get_status(self) ->AirLockStatus:

        query = 'SELECT * FROM c'
        data = await self.query(query=query)
        if data and len(data) > 0:
            return parse_obj_as(AirLockStatus, data[0])
        else:
            return None





