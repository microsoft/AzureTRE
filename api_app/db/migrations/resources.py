import uuid
from db.repositories.operations import OperationRepository
from db.repositories.resources import ResourceRepository
from db.repositories.resources_history import ResourceHistoryRepository


class ResourceMigration(ResourceRepository):
    @classmethod
    async def create(cls):
        cls = ResourceMigration()
        resource_repo = await super().create()
        cls._container = resource_repo._container
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

    async def archive_history(self, resource_history_repository: ResourceHistoryRepository) -> int:
        num_updated = 0
        for resource in await self.query("SELECT * from c WHERE IS_DEFINED(c.history)"):
            for history_item in resource['history']:
                history_item['id'] = str(uuid.uuid4())
                history_item['resourceId'] = resource['id']
                await resource_history_repository.update_item_dict(history_item)
            # Remove the history item from the resource
            del resource['history']
            await self.update_item_dict(resource)
            num_updated = num_updated + 1

        return num_updated

    async def migrate_step_id_of_operation_steps(self, operations_repository: OperationRepository) -> int:
        num_updated = 0
        for operation in await operations_repository.query("SELECT * from c WHERE ARRAY_LENGTH(c.steps) > 0 AND IS_DEFINED(c.steps[0].stepId)"):
            for operation_step in operation['steps']:
                operation_step['templateStepId'] = operation_step['stepId']
                operation_step['id'] = str(uuid.uuid4())
                del operation_step['stepId']

            await operations_repository.update_item_dict(operation)
            num_updated = num_updated + 1

        return num_updated
