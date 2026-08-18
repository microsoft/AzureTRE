from fastapi import APIRouter, Depends, HTTPException, status
from auth.rbac import require_tre_admin
from resources import strings
from models.schemas.migrations import Migration, MigrationOutList
from db.repositories.workspaces import WorkspaceRepository
from db.repositories.airlock_requests import AirlockRequestRepository
from services.logging import logger

migrations_core_router = APIRouter(dependencies=[Depends(require_tre_admin)])


@migrations_core_router.post("/migrations",
                             status_code=status.HTTP_202_ACCEPTED,
                             name=strings.API_MIGRATE_DATABASE,
                             response_model=MigrationOutList,
                             dependencies=[Depends(require_tre_admin)])
async def migrate_database():
    try:
        migrations = list()

        # ADD MIGRATIONS HERE
        # Examples of migrations can be found in this file:
        # https://github.com/microsoft/AzureTRE/blob/v0.22.0/api_app/api/routes/migrations.py#L32-L84
        # and this folder:
        # https://github.com/microsoft/AzureTRE/tree/v0.22.0/api_app/db/migrations

        # Preserve legacy storage routing for pre-v2 workspaces.
        workspace_repo = await WorkspaceRepository.create()
        migrated_ids = await workspace_repo.set_default_airlock_version_for_legacy_workspaces()
        logger.info(f"Set default airlock_version=1 on {len(migrated_ids)} legacy workspace(s).")
        migrations.append(Migration(issueNumber="5048", status=f"Set airlock_version=1 on {len(migrated_ids)} legacy workspace(s)"))

        # Preserve legacy storage routing for in-flight pre-v2 requests.
        airlock_request_repo = await AirlockRequestRepository.create()
        migrated_request_ids = await airlock_request_repo.set_default_airlock_version_for_legacy_requests()
        logger.info(f"Set default airlock_version=1 on {len(migrated_request_ids)} legacy airlock request(s).")
        migrations.append(Migration(issueNumber="5048", status=f"Set airlock_version=1 on {len(migrated_request_ids)} legacy airlock request(s)"))

        return MigrationOutList(migrations=migrations)
    except Exception as e:
        logger.exception("Failed to migrate database")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
