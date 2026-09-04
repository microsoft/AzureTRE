import json
from typing import Optional

from db.repositories.resources import ResourceRepository
from db.repositories.resource_templates import ResourceTemplateRepository
from db.repositories.resources_history import ResourceHistoryRepository
from service_bus.helpers import send_deployment_message, update_resource_for_step
from models.domain.authentication import User

from models.domain.request_action import RequestAction
from models.domain.resource import Resource, ResourceType
from models.domain.operation import Operation, get_failure_status_for_action

from db.repositories.operations import OperationRepository, extract_workspace_id_from_resource_path
from services.logging import logger, tracer


async def send_resource_request_message(resource: Resource, operations_repo: OperationRepository, resource_repo: ResourceRepository, user: User, resource_template_repo: ResourceTemplateRepository, resource_history_repo: ResourceHistoryRepository, action: RequestAction = RequestAction.Install, is_cascade: str = False, operation_id: Optional[str] = None) -> Operation:
    """
    Creates and sends a resource request message for the resource to the Service Bus.
    The resource ID is added to the message to serve as an correlation ID for the deployment process.

    :param resource: The resource to deploy.
    :param action: install, uninstall etc.
    """
    with tracer.start_as_current_span("send_resource_request_message") as current_span:
        current_span.set_attribute("resource_id", resource.id)
        current_span.set_attribute("action", action)

        #  Construct the resources to build an operation item for
        resources_list = []
        if is_cascade:
            resources_list = await resource_repo.get_resource_dependency_list(resource)
        else:
            resources_list.append(resource.__dict__)

        # add the operation to the db - this will create all the steps needed (if any are defined in the template)
        operation = await operations_repo.create_operation_item(
            resource_id=resource.id,
            resource_list=resources_list,
            action=action,
            resource_path=resource.resourcePath,
            resource_version=resource.resourceVersion,
            user=user,
            resource_repo=resource_repo,
            resource_template_repo=resource_template_repo,
            operation_id=operation_id)
        current_span.set_attribute("operation_id", operation.id)

        try:
            # prep the first step to send in SB
            # resource at this point is the original object with unmaskked values
            first_step = operation.steps[0]
            current_span.set_attribute("step_id", first_step.id)
            resource_to_send = await update_resource_for_step(
                operation_step=first_step,
                resource_repo=resource_repo,
                resource_template_repo=resource_template_repo,
                resource_history_repo=resource_history_repo,
                root_resource=resource,
                step_resource=None,
                resource_to_update_id=first_step.resourceId,
                primary_action=action,
                user=user)

            # create + send the message
            content = json.dumps(resource_to_send.get_resource_request_message_payload(operation_id=operation.id, step_id=first_step.id, action=first_step.resourceAction))
            await send_deployment_message(content=content, correlation_id=operation.id, session_id=first_step.resourceId, action=first_step.resourceAction)
        except Exception:
            logger.exception(f"Failed to dispatch initial deployment message for operation {operation.id}")
            try:
                operation.status = get_failure_status_for_action(action)
                operation.message = f"Failed to dispatch initial deployment message: {action}"
                if operation.steps:
                    first_step = operation.steps[0]
                    first_step.status = get_failure_status_for_action(first_step.resourceAction)
                    first_step.message = f"Failed to dispatch initial deployment message: {first_step.resourceAction}"
                # Keep lease held during caller compensation; caller will release lease upon completing rollback
                await operations_repo.update_item(operation, release_lease=False)
            except Exception:
                logger.exception(f"Failed to persist failure state for operation {operation.id}")
                # Fallback: remove orphaned operation and release its workspace lease
                try:
                    del_call = operations_repo.delete_item(operation.id)
                    if hasattr(del_call, "__await__"):
                        await del_call
                except Exception:
                    logger.exception(f"Failed to delete orphaned operation {operation.id}")
                target_workspace_id = extract_workspace_id_from_resource_path(resource.resourcePath)
                if not target_workspace_id:
                    if getattr(resource, "resourceType", None) == ResourceType.Workspace:
                        target_workspace_id = resource.id
                    elif hasattr(resource, "workspaceId") and resource.workspaceId:
                        target_workspace_id = resource.workspaceId
                if target_workspace_id and hasattr(operations_repo, "release_workspace_lease"):
                    try:
                        rel_call = operations_repo.release_workspace_lease(target_workspace_id, operation.id)
                        if hasattr(rel_call, "__await__"):
                            await rel_call
                    except Exception:
                        logger.exception(f"Failed to release workspace lease for {target_workspace_id}")
            raise

    return operation
