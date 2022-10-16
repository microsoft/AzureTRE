from typing import List
import logging

from models.domain.airlock_request import AirlockRequest
from models.domain.resource import ResourceType
from models.domain.operation import Operation
from models.domain.authentication import User
from api.routes.resource_helpers import send_uninstall_message
from db.repositories.resource_templates import ResourceTemplateRepository
from db.repositories.user_resources import UserResourceRepository
from db.repositories.workspace_services import WorkspaceServiceRepository
from db.repositories.operations import OperationRepository


async def remove_review_user_resource(
        airlock_request: AirlockRequest,
        user_resource_repo: UserResourceRepository,
        workspace_service_repo: WorkspaceServiceRepository,
        resource_template_repo: ResourceTemplateRepository,
        operations_repo: OperationRepository,
        user: User) -> List[Operation]:
    operations: List[Operation] = []
    for review_ur in airlock_request.reviewUserResources:
        user_resource = user_resource_repo.get_user_resource_by_id(
            workspace_id=review_ur.workspaceId,
            service_id=review_ur.workspaceServiceId,
            resource_id=review_ur.userResourceId
        )

        workspace_service = workspace_service_repo.get_workspace_service_by_id(workspace_id=user_resource.workspaceId, service_id=user_resource.parentWorkspaceServiceId)

        resource_template = resource_template_repo.get_template_by_name_and_version(
            user_resource.templateName,
            user_resource.templateVersion,
            ResourceType.UserResource,
            workspace_service.templateName)

        logging.info(f"Deleting user resource {user_resource.id} in workspace service {workspace_service.id}")
        operations.append(await send_uninstall_message(
            resource=user_resource,
            resource_repo=user_resource_repo,
            operations_repo=operations_repo,
            resource_type=ResourceType.UserResource,
            resource_template_repo=resource_template_repo,
            user=user,
            resource_template=resource_template))
        logging.info(f"Started operation {operations[-1]}")

    logging.info(f"Started {len(operations)} operations on deleting user resources")
    return operations
