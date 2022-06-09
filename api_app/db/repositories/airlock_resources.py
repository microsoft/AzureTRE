from datetime import datetime
from azure.cosmos import CosmosClient
from models.domain.airlock_resource import AirlockResource, AirlockResourceHistoryItem
from models.domain.authentication import User
from core import config
from db.repositories.base import BaseRepository


class AirlockResourceRepository(BaseRepository):
    def __init__(self, client: CosmosClient):
        super().__init__(client, config.STATE_STORE_AIRLOCK_RESOURCES_CONTAINER)

    @staticmethod
    def get_resource_base_spec_params():
        return {"tre_id": config.TRE_ID}

    def get_timestamp(self) -> float:
        return datetime.utcnow().timestamp()

    def update_airlock_resource_item(self, original_resource: AirlockResource, new_resource: AirlockResource, user: User) -> AirlockResource:
        history_item = AirlockResourceHistoryItem(
            resourceVersion=original_resource.resourceVersion,
            updatedWhen=original_resource.updatedWhen,
            user=original_resource.user,
            previousStatus=original_resource.status
        )
        new_resource.history.append(history_item)

        # now update the resource props
        new_resource.resourceVersion = new_resource.resourceVersion + 1
        new_resource.user = user
        new_resource.updatedWhen = self.get_timestamp()

        # TODO https://github.com/microsoft/AzureTRE/issues/2016
        self.update_item(new_resource)
        return new_resource
