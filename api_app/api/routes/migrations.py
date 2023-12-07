from fastapi import APIRouter, Depends, HTTPException, status
from db.migrations.airlock import AirlockMigration
from db.migrations.resources import ResourceMigration
from db.repositories.operations import OperationRepository
from db.repositories.resources_history import ResourceHistoryRepository
from services.authentication import get_current_admin_user
from resources import strings
from api.dependencies.database import get_repository
from db.migrations.shared_services import SharedServiceMigration
from db.migrations.workspaces import WorkspaceMigration
from db.repositories.resources import ResourceRepository
from models.schemas.migrations import MigrationOutList, Migration
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
        logger.info("PR 1030")
        await resources_repo.rename_field_name('resourceTemplateName', 'templateName')
        await resources_repo.rename_field_name('resourceTemplateVersion', 'templateVersion')
        await resources_repo.rename_field_name('resourceTemplateParameters', 'properties')
        migrations.append(Migration(issueNumber="PR 1030", status="Executed"))

        logger.info("PR 1031")
        await resources_repo.rename_field_name('workspaceType', 'templateName')
        await resources_repo.rename_field_name('workspaceServiceType', 'templateName')
        await resources_repo.rename_field_name('userResourceType', 'templateName')
        migrations.append(Migration(issueNumber="PR 1031", status="Executed"))

        logger.info("PR 1717 - Shared services")
        migration_status = "Executed" if await shared_services_migration.deleteDuplicatedSharedServices() else "Skipped"
        migrations.append(Migration(issueNumber="PR 1717", status=migration_status))

        logger.info("PR 1726 - Authentication needs to be in properties so we can update them")
        migration_status = "Executed" if await workspace_migration.moveAuthInformationToProperties() else "Skipped"
        migrations.append(Migration(issueNumber="PR 1726", status=migration_status))

        logger.info("PR 1406 - Extra field to support UI")
        num_rows = await resource_migration.add_deployment_status_field(operations_repo)
        migrations.append(Migration(issueNumber="1406", status=f'Updated {num_rows} resource objects'))

        logger.info("PR 3066 - Archive resources history")
        num_rows = await resource_migration.archive_history(resource_history_repo)
        migrations.append(Migration(issueNumber="3066", status=f'Updated {num_rows} resource objects'))

        logger.info("PR 2371 - Validate min firewall version")
        await shared_services_migration.checkMinFirewallVersion()
        migrations.append(Migration(issueNumber="2371", status='Firewall version meets requirement'))

        logger.info("PR 2779 - Restructure Airlock requests & add createdBy field")
        await airlock_migration.rename_field_name('requestType', 'type')
        await airlock_migration.rename_field_name('requestTitle', 'title')
        await airlock_migration.rename_field_name('user', 'updatedBy')
        await airlock_migration.rename_field_name('creationTime', 'createdWhen')
        num_updated = await airlock_migration.add_created_by_and_rename_in_history()
        migrations.append(Migration(issueNumber="2779", status=f'Renamed fields & updated {num_updated} airlock requests with createdBy'))

        logger.info("PR 2883 - Support multiple reviewer VMs per Airlock request")
        num_updated = await airlock_migration.change_review_resources_to_dict()
        migrations.append(Migration(issueNumber="2883", status=f'Updated {num_updated} airlock requests with new reviewUserResources format'))

        logger.info("PR 3152 - Migrate reviewDecision of Airlock Reviews")
        num_updated = await airlock_migration.update_review_decision_values()
        migrations.append(Migration(issueNumber="3152", status=f'Updated {num_updated} airlock requests with new reviewDecision value'))

        logger.info("PR 3358 - Migrate OperationSteps of Operations")
        num_updated = await resource_migration.migrate_step_id_of_operation_steps(operations_repo)
        migrations.append(Migration(issueNumber="3358", status=f'Updated {num_updated} operations'))

        return MigrationOutList(migrations=migrations)
    except Exception as e:
        logger.exception("Failed to migrate database")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
