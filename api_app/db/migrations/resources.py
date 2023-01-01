from azure.cosmos.aio import CosmosClient
from db.repositories.operations import OperationRepository
from db.repositories.resources import ResourceRepository


class ResourceMigration(ResourceRepository):
    @classmethod
    async def create(cls, client: CosmosClient):
        cls = ResourceMigration()
        resource_repo = await super().create(client)
        cls._container = resource_repo._container
        cls._client = resource_repo._client
        return cls

    async def add_deployment_status_field(self, operations_repository: OperationRepository) -> int:
        num_updated = 0
        for resource in await self.query("SELECT * from c WHERE NOT IS_DEFINED(c.deploymentStatus)"):
            # For each resource, find the last operation, if it exists
            id = resource['id']
            op = await operations_repository.query(f'SELECT * from c WHERE c.resourceId = "{id}" ORDER BY c._ts DESC OFFSET 0 LIMIT 1')
            if op:
                # Set the deploymentStatus of the resource to be the status fo its last operation
                resource['deploymentStatus'] = op[0]['status']
                await self.update_item_dict(resource)
                num_updated = num_updated + 1

        return num_updated
