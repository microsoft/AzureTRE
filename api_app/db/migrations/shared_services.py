import logging

from azure.cosmos import CosmosClient
from db.repositories.shared_services import SharedServiceRepository


class SharedServiceMigration(SharedServiceRepository):
    def __init__(self, client: CosmosClient):
        super().__init__(client)

    def deleteDuplicatedSharedServices(self) -> bool:
        template_names = ['tre-shared-service-firewall', 'tre-shared-service-nexus', 'tre-shared-service-gitea']

        migrated = False
        for template_name in template_names:
            for item in self.query(query=f'SELECT * FROM c WHERE c.resourceType = "shared-service" AND c.templateName = "{template_name}" \
                                                                ORDER BY c.updatedWhen ASC OFFSET 1 LIMIT 10000'):
                logging.INFO(f"Deleting element {item}")
                self.delete_item(item, partition_key=item["id"])
                migrated = True

        return migrated
