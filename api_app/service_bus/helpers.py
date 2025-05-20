from azure.servicebus import ServiceBusMessage
from azure.servicebus.aio import ServiceBusClient
from pydantic import parse_obj_as
from resources import strings
from db.repositories.resources_history import ResourceHistoryRepository
from service_bus.substitutions import substitute_properties
from models.domain.resource_template import PipelineStep
from models.domain.operation import OperationStep
from models.domain.resource import Resource, ResourceType
from db.repositories.resource_templates import ResourceTemplateRepository
from models.domain.authentication import User
from models.schemas.resource import ResourcePatch
from db.repositories.resources import ResourceRepository
from core import config, credentials
from services.logging import logger
from azure.cosmos.exceptions import CosmosAccessConditionFailedError


async def _send_message(message: ServiceBusMessage, queue: str):
    """
    Sends the given message to the given queue in the Service Bus.

    :param message: The message to send.
    :type message: ServiceBusMessage
    :param queue: The Service Bus queue to send the message to.
    :type queue: str
    """
    async with credentials.get_credential_async_context() as credential:
        service_bus_client = ServiceBusClient(config.SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE, credential)

        async with service_bus_client:
            sender = service_bus_client.get_queue_sender(queue_name=queue)

            async with sender:
                await sender.send_messages(message)


async def send_deployment_message(content, correlation_id, session_id, action):
    resource_request_message = ServiceBusMessage(body=content, correlation_id=correlation_id, session_id=session_id)
    logger.info(f"Sending resource request message with correlation ID {resource_request_message.correlation_id}, action: {action}")
    await _send_message(resource_request_message, config.SERVICE_BUS_RESOURCE_REQUEST_QUEUE)


async def update_resource_for_step(operation_step: OperationStep, resource_repo: ResourceRepository, resource_template_repo: ResourceTemplateRepository, resource_history_repo: ResourceHistoryRepository, root_resource: Resource, step_resource: Resource, resource_to_update_id: str, primary_action: str, user: User) -> Resource:
    # step_resource is the resource instance where the step was defined. e.g. 'add firewall rule' step defined in Guacamole template -> the step_resource is the Guacamole ws service.
    # root_resource is theresource on which the user chose to update, i.e. the top most resource in cascaded action or the same resource in a non-cascaded action.
    if step_resource is None:
        step_resource = await resource_repo.get_resource_by_id(operation_step.sourceTemplateResourceId)

    # If we are handling the root resource, we can leverage the given resource which has non redacted properties
    if root_resource is not None and root_resource.id == step_resource.id:
        step_resource = root_resource

    step_resource_parent_service_name = ""
    step_resource_parent_workspace = None
    step_resource_parent_workspace_service = None
    if step_resource.resourceType == ResourceType.UserResource:
        step_resource_parent_workspace_service = await resource_repo.get_resource_by_id(step_resource.parentWorkspaceServiceId)
        step_resource_parent_service_name = step_resource_parent_workspace_service.templateName
        step_resource_parent_workspace = await resource_repo.get_resource_by_id(step_resource.workspaceId)

    if step_resource.resourceType == ResourceType.WorkspaceService:
        step_resource_parent_workspace = await resource_repo.get_resource_by_id(step_resource.workspaceId)

    parent_template = await resource_template_repo.get_template_by_name_and_version(step_resource.templateName, step_resource.templateVersion, step_resource.resourceType, step_resource_parent_service_name)

    # if there are no pipelines, or custom action, no need to continue with substitutions.
    if not parent_template.pipeline:
        return step_resource

    parent_template_pipeline_dict = parent_template.pipeline.dict()

    # if action not defined as a pipeline, custom action, no need to continue with substitutions.
    if primary_action not in parent_template_pipeline_dict:
        return step_resource

    pipeline_primary_action = parent_template_pipeline_dict[primary_action]
    is_first_main_step = pipeline_primary_action and len(pipeline_primary_action) == 1 and pipeline_primary_action[0]['stepId'] == 'main'
    if not pipeline_primary_action or is_first_main_step:
        return step_resource

    # get the template step
    template_step = None
    for step in parent_template_pipeline_dict[primary_action]:
        if step["stepId"] == operation_step.templateStepId:
            template_step = parse_obj_as(PipelineStep, step)
            if (template_step.resourceAction is None and primary_action == strings.RESOURCE_ACTION_INSTALL):
                template_step.resourceAction = strings.RESOURCE_ACTION_INSTALL
            break

    if template_step is None:
        raise Exception(f"Cannot find step with id of {operation_step.templateStepId} in template {step_resource.templateName} for action {primary_action}")

    resource_to_send = await try_update_with_retries(
        num_retries=3,
        attempt_count=0,
        resource_repo=resource_repo,
        resource_template_repo=resource_template_repo,
        resource_history_repo=resource_history_repo,
        user=user,
        resource_to_update_id=resource_to_update_id,
        template_step=template_step,
        primary_resource=step_resource,
        primary_parent_workspace=step_resource_parent_workspace,
        primary_parent_workspace_svc=step_resource_parent_workspace_service
    )

    return resource_to_send


async def try_update_with_retries(num_retries: int, attempt_count: int, resource_repo: ResourceRepository, resource_template_repo: ResourceTemplateRepository, resource_history_repo: ResourceHistoryRepository, user: User, resource_to_update_id: str, template_step: PipelineStep, primary_resource: Resource, primary_parent_workspace: Resource = None, primary_parent_workspace_svc: Resource = None) -> Resource:
    try:
        return await try_patch(
            resource_repo=resource_repo,
            resource_template_repo=resource_template_repo,
            resource_history_repo=resource_history_repo,
            user=user,
            resource_to_update_id=resource_to_update_id,
            template_step=template_step,
            primary_resource=primary_resource,
            primary_parent_workspace=primary_parent_workspace,
            primary_parent_workspace_svc=primary_parent_workspace_svc
        )
    except CosmosAccessConditionFailedError as e:
        logger.warning(f"Etag mismatch for {resource_to_update_id}. Retrying.")
        if attempt_count < num_retries:
            await try_update_with_retries(
                num_retries=num_retries,
                attempt_count=(attempt_count + 1),
                resource_repo=resource_repo,
                resource_template_repo=resource_template_repo,
                resource_history_repo=resource_history_repo,
                user=user,
                resource_to_update_id=resource_to_update_id,
                template_step=template_step,
                primary_resource=primary_resource,
                primary_parent_workspace=primary_parent_workspace,
                primary_parent_workspace_svc=primary_parent_workspace_svc
            )
        else:
            raise e


async def try_patch(resource_repo: ResourceRepository, resource_template_repo: ResourceTemplateRepository, resource_history_repo: ResourceHistoryRepository, user: User, resource_to_update_id: str, template_step: PipelineStep, primary_resource: Resource, primary_parent_workspace: Resource, primary_parent_workspace_svc: Resource) -> Resource:
    resource_to_update = await resource_repo.get_resource_by_id(resource_to_update_id)

    # substitute values into new property bag for update
    properties = substitute_properties(template_step, primary_resource, primary_parent_workspace, primary_parent_workspace_svc, resource_to_update)

    # get the template for the resource to upgrade
    parent_service_name = ""
    if resource_to_update.resourceType == ResourceType.UserResource:
        parent_service_name = primary_parent_workspace_svc.templateName

    resource_template_to_send = await resource_template_repo.get_template_by_name_and_version(resource_to_update.templateName, resource_to_update.templateVersion, resource_to_update.resourceType, parent_service_name)

    # create the patch
    patch = ResourcePatch(
        properties=properties
    )

    # validate and submit the patch
    resource_to_send, _ = await resource_repo.patch_resource(
        resource=resource_to_update,
        resource_patch=patch,
        resource_template=resource_template_to_send,
        etag=resource_to_update.etag,
        resource_template_repo=resource_template_repo,
        resource_history_repo=resource_history_repo,
        user=user,
        resource_action=template_step.resourceAction)

    return resource_to_send
