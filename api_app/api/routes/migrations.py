from fastapi import APIRouter, Depends, HTTPException, status
from services.authentication import get_current_admin_user
from resources import strings
from models.schemas.migrations import MigrationOutList
from services.logging import logger

migrations_core_router = APIRouter(dependencies=[Depends(get_current_admin_user)])


@migrations_core_router.post("/migrations",
                             status_code=status.HTTP_202_ACCEPTED,
                             name=strings.API_MIGRATE_DATABASE,
                             response_model=MigrationOutList,
                             dependencies=[Depends(get_current_admin_user)])
async def migrate_database():
    try:
        migrations = list()

        # ADD MIGRATIONS HERE
        # Examples of migrations can be found in this file:
        # https://github.com/microsoft/AzureTRE/blob/v0.22.0/api_app/api/routes/migrations.py#L32-L84
        # and this folder:
        # https://github.com/microsoft/AzureTRE/tree/v0.22.0/api_app/db/migrations
        logger.info("No migrations exist.")

        return MigrationOutList(migrations=migrations)
    except Exception as e:
        logger.exception("Failed to migrate database")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
