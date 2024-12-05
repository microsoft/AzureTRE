from fastapi import APIRouter, Depends, HTTPException, status
from db.migrations.airlock import AirlockMigration
from db.migrations.resources import ResourceMigration
from api.helpers import get_repository
from db.repositories.operations import OperationRepository
from db.repositories.resources_history import ResourceHistoryRepository
from services.authentication import get_current_admin_user
from resources import strings
from db.migrations.shared_services import SharedServiceMigration
from db.migrations.workspaces import WorkspaceMigration
from db.repositories.resources import ResourceRepository
from models.schemas.migrations import MigrationOutList
from services.logging import logger

migrations_core_router = APIRouter(dependencies=[Depends(get_current_admin_user)])


@migrations_core_router.post("/migrations",
                             status_code=status.HTTP_202_ACCEPTED,
                             name=strings.API_MIGRATE_DATABASE,
                             response_model=MigrationOutList,
                             dependencies=[Depends(get_current_admin_user)])
async def migrate_database(resources_repo=Depends(get_repository(ResourceRepository)),
                           operations_repo=Depends(get_repository(OperationRepository)),
                           resource_history_repo=Depends(get_repository(ResourceHistoryRepository)),
                           shared_services_migration=Depends(get_repository(SharedServiceMigration)),
                           workspace_migration=Depends(get_repository(WorkspaceMigration)),
                           resource_migration=Depends(get_repository(ResourceMigration)),
                           airlock_migration=Depends(get_repository(AirlockMigration)),):
    try:
        migrations = list()

        # ADD MIGRATIONS HERE

        return MigrationOutList(migrations=migrations)
    except Exception as e:
        logger.exception("Failed to migrate database")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
