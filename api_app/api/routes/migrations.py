from fastapi import APIRouter, Depends, HTTPException, status
from auth.rbac import require_tre_admin
from resources import strings
from models.schemas.migrations import Migration, MigrationOutList
from db.repositories.resource_templates import ResourceTemplateRepository
from db.repositories.resources import ResourceRepository
from db.repositories.resources_history import ResourceHistoryRepository
from db.repositories.workspaces import WorkspaceRepository
from services.logging import logger

migrations_core_router = APIRouter(dependencies=[Depends(require_tre_admin)])


@migrations_core_router.post(
    "/migrations",
    status_code=status.HTTP_202_ACCEPTED,
    name=strings.API_MIGRATE_DATABASE,
    response_model=MigrationOutList,
    dependencies=[Depends(require_tre_admin)],
)
async def migrate_database():
    try:
        migrations = list()

        # Preserve legacy storage routing for pre-v2 workspaces, which the bundle would otherwise
        # redeploy as v2 and destroy their legacy storage.
        workspace_repo = await WorkspaceRepository.create()
        migrated_ids = await workspace_repo.set_default_airlock_version_for_legacy_workspaces()
        logger.info(f"Set default airlock_version=1 on {len(migrated_ids)} legacy workspace(s).")
        migrations.append(
            Migration(issueNumber="5048", status=f"Set airlock_version=1 on {len(migrated_ids)} legacy workspace(s)")
        )

        # Updates stored real sensitive values before the API masked them, as it does at the install.
        resource_repo = await ResourceRepository.create()
        changed_resources, changed_history_items = await resource_repo.mask_stored_sensitive_values(
            await ResourceTemplateRepository.create(), await ResourceHistoryRepository.create()
        )
        logger.info(
            f"Masked sensitive values in {changed_resources} resource(s) and {changed_history_items} history item(s)."
        )
        migrations.append(
            Migration(
                issueNumber="5298",
                status=f"Masked sensitive values in {changed_resources} resource(s) and {changed_history_items} history item(s)",
            )
        )

        return MigrationOutList(migrations=migrations)
    except Exception as e:
        logger.exception("Failed to migrate database")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
