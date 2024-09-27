import json

from db.repositories.resources import ResourceRepository
from db.repositories.resource_templates import ResourceTemplateRepository
from db.repositories.resources_history import ResourceHistoryRepository
from service_bus.helpers import send_deployment_message, update_resource_for_step
from models.domain.authentication import User

from models.domain.request_action import RequestAction
from models.domain.resource import Resource
from models.domain.operation import Operation

from db.repositories.operations import OperationRepository
from services.logging import tracer


async def send_resource_request_message(resource: Resource, operations_repo: OperationRepository, resource_repo: ResourceRepository, user: User, resource_template_repo: ResourceTemplateRepository, resource_history_repo: ResourceHistoryRepository, action: RequestAction = RequestAction.Install, is_cascade: str = False) -> Operation:
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
            resource_template_repo=resource_template_repo)
        current_span.set_attribute("operation_id", operation.id)

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

    return operation
