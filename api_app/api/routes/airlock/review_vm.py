from typing import List
import logging
from pydantic import parse_obj_as

from models.domain.user_resource import UserResource
from models.domain.resource import ResourceType
from models.domain.operation import Operation
from api.routes.resource_helpers import send_uninstall_message


async def remove_review_vms(request_id: str, user_resource_repo, workspace_service_repo, resource_template_repo, operations_repo, user) -> List[Operation]:
    # review_vms = user_resource_repo.query(f"SELECT * FROM c WHERE IS_DEFINED(c.properties.airlock_request_id) \
    #     AND c.properties.airlock_request_id = '{request_id}'")
    review_vms = user_resource_repo.query(f"SELECT * FROM c where is_defined(c.properties.airlock_request_sas_url) \
        and contains(c.properties.airlock_request_sas_url, '{request_id}')")

    if len(review_vms) == 0:
        logging.warning(f"There are no user resources with airlock_request_id = {request_id}")

    operations: List[Operation] = []
    for review_vm in review_vms:
        user_resource = parse_obj_as(UserResource, review_vm)

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
