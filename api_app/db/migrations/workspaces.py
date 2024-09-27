import semantic_version

from db.repositories.workspaces import WorkspaceRepository
from services.logging import logger


class WorkspaceMigration(WorkspaceRepository):
    @classmethod
    async def create(cls):
        cls = WorkspaceMigration()
        resource_repo = await super().create()
        cls._container = resource_repo._container
        return cls

    async def moveAuthInformationToProperties(self) -> bool:
        migrated = False
        for item in await self.query(query=WorkspaceRepository.workspaces_query_string()):
            template_version = semantic_version.Version(item["templateVersion"])
            updated = False
            if (template_version < semantic_version.Version('0.2.7')):

                # Rename app_id to be client_id
                if "app_id" in item["properties"]:
                    item["properties"]["client_id"] = item["properties"]["app_id"]
                    del item["properties"]["app_id"]
                    updated = True

                if "scope_id" not in item["properties"]:
                    item["properties"]["scope_id"] = f"api://{item['properties']['client_id']}"
                    updated = True

                if "authInformation" in item:
                    logger.info(f'Upgrading authInformation in workspace {item["id"]}')

                    # Copy authInformation into properties
                    item["properties"]["sp_id"] = item["authInformation"]["sp_id"]
                    item["properties"]["app_role_id_workspace_researcher"] = item["authInformation"]["roles"]["WorkspaceResearcher"]
                    item["properties"]["app_role_id_workspace_owner"] = item["authInformation"]["roles"]["WorkspaceOwner"]
                    # cleanup
                    del item["authInformation"]
                    updated = True

                if updated:
                    await self.update_item_dict(item)
                    logger.info(f'Upgraded authentication info for workspace id {item["id"]}')
                    migrated = True

            return migrated
