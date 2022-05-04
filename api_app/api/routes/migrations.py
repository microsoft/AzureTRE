import logging

from fastapi import APIRouter, Depends, HTTPException, status
from services.authentication import get_current_admin_user
from resources import strings
from api.dependencies.database import get_repository
from db.migrations.shared_services import SharedServiceMigration
from db.migrations.workspaces import WorkspaceMigration
from db.repositories.resources import ResourceRepository


migrations_core_router = APIRouter(dependencies=[Depends(get_current_admin_user)])


@migrations_core_router.post("/migrations",
                             status_code=status.HTTP_202_ACCEPTED,
                             name=strings.API_MIGRATE_DATABASE,
                             dependencies=[Depends(get_current_admin_user)])
async def migrate_database(resources_repo=Depends(get_repository(ResourceRepository)),
                           shared_services_migration=Depends(get_repository(SharedServiceMigration)),
                           workspace_migration=Depends(get_repository(WorkspaceMigration))):
    try:
        logging.info("PR 1030.")
        resources_repo.rename_field_name('resourceTemplateName', 'templateName')
        resources_repo.rename_field_name('resourceTemplateVersion', 'templateVersion')
        resources_repo.rename_field_name('resourceTemplateParameters', 'properties')

        logging.info("PR 1031.")
        resources_repo.rename_field_name('workspaceType', 'templateName')
        resources_repo.rename_field_name('workspaceServiceType', 'templateName')
        resources_repo.rename_field_name('userResourceType', 'templateName')

        logging.info("PR 1717. - Shared services")
        await shared_services_migration.deleteDuplicatedSharedServices()

        logging.info("PR 1726. - Authentication needs to be in properties so we can update them")
        await workspace_migration.moveAuthInformationToProperties()
    except Exception as e:
        logging.error(f"Failed to migrate database: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
