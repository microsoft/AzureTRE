import semantic_version

from db.repositories.shared_services import SharedServiceRepository
from db.repositories.resources import IS_ACTIVE_RESOURCE
from services.logging import logger


class SharedServiceMigration(SharedServiceRepository):
    @classmethod
    async def create(cls):
        cls = SharedServiceMigration()
        resource_repo = await super().create()
        cls._container = resource_repo._container
        return cls

    async def deleteDuplicatedSharedServices(self) -> bool:
        template_names = ['tre-shared-service-firewall', 'tre-shared-service-sonatype-nexus', 'tre-shared-service-gitea']

        migrated = False
        for template_name in template_names:
            for item in await self.query(query=f'SELECT * FROM c WHERE c.resourceType = "shared-service" \
                                           AND c.templateName = "{template_name}" AND {IS_ACTIVE_RESOURCE} \
                                           ORDER BY c.updatedWhen ASC OFFSET 1 LIMIT 10000'):
                template_version = semantic_version.Version(item["templateVersion"])
                if (template_version < semantic_version.Version('0.3.0')):
                    logger.info(f'Deleting element {item["id"]}')
                    await self.delete_item(item["id"])
                    migrated = True

        return migrated

    async def checkMinFirewallVersion(self) -> bool:
        template_name = 'tre-shared-service-firewall'
        min_template_version = semantic_version.Version('0.4.0')

        resources = await self.query(query=f'SELECT * FROM c WHERE c.resourceType = "shared-service" \
                                      AND c.templateName = "{template_name}" AND {IS_ACTIVE_RESOURCE}')

        if not resources:
            raise ValueError(f"Expecting to have an instance of Firewall (template name {template_name}) deployed in a successful TRE deployment")

        template_version = semantic_version.Version(resources[0]["templateVersion"])

        if (template_version < min_template_version):
            raise ValueError(f"{template_name} deployed version ({template_version}) is below minimum ({min_template_version})!",
                             "Go to https://github.com/microsoft/AzureTRE/blob/main/CHANGELOG.md, and review release 0.5.0 for more info.")

        return True
