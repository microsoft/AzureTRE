from azure.cosmos import CosmosClient
from db.repositories.shared_services import SharedServiceRepository


class SharedServiceMigration(SharedServiceRepository):
    def __init__(self, client: CosmosClient):
        super().__init__(client)

    async def deleteDuplicatedSharedServices(self):
        template_names = ['tre-shared-service-firewall', 'tre-shared-service-nexus', 'tre-shared-service-gitea']

        for template_name in template_names:
            for item in self.query(query=f'SELECT * FROM c WHERE c.resourceType = "shared-service" AND c.templateName = "{template_name}" \
                                                                ORDER BY c.updatedWhen ASC OFFSET 1 LIMIT 10000', enable_cross_partition_query=True):
                print(f"Deleting element {item}")
                self.delete_item(item, partition_key=item["id"])
