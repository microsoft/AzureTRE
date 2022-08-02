import logging

from azure.cosmos import CosmosClient
from db.repositories.shared_services import SharedServiceRepository
from db.repositories.resources import IS_OPERATING_SHARED_SERVICE
import semantic_version


class SharedServiceMigration(SharedServiceRepository):
    def __init__(self, client: CosmosClient):
        super().__init__(client)

    def deleteDuplicatedSharedServices(self) -> bool:
        template_names = ['tre-shared-service-firewall', 'tre-shared-service-nexus', 'tre-shared-service-gitea']

        migrated = False
        for template_name in template_names:
            for item in self.query(query=f'SELECT * FROM c WHERE c.resourceType = "shared-service" \
                                           AND c.templateName = "{template_name}" AND {IS_OPERATING_SHARED_SERVICE} \
                                           ORDER BY c.updatedWhen ASC OFFSET 1 LIMIT 10000'):
                template_version = semantic_version.Version(item["templateVersion"])
                if (template_version < semantic_version.Version('0.3.0')):
                    logging.info(f'Deleting element {item["id"]}')
                    self.delete_item(item["id"])
                    migrated = True

        return migrated

    def checkMinFirewallVersion(self) -> bool:
        template_name = 'tre-shared-service-firewall'
        min_template_version = semantic_version.Version('0.4.0')

        resource = self.query(query=f'SELECT * FROM c WHERE c.resourceType = "shared-service" \
                                      AND c.templateName = "{template_name}" AND {IS_OPERATING_SHARED_SERVICE}')

        template_version = semantic_version.Version(resource[0]["templateVersion"])

        if (template_version < min_template_version):
            raise ValueError(f"{template_name} deployed version ({template_version}) is below minimum ({min_template_version})!",
                             " Go to https://github.com/microsoft/AzureTRE/blob/main/CHANGELOG.md#050 for more info.")

        return True
