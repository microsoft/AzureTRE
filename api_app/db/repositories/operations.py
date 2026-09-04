from datetime import datetime, UTC
import uuid
from typing import List, Optional

from azure.core import MatchConditions
from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
from azure.cosmos.exceptions import CosmosResourceExistsError, CosmosAccessConditionFailedError, CosmosResourceNotFoundError
from fastapi import HTTPException, status as http_status
from pydantic import TypeAdapter
from db.repositories.resource_templates import ResourceTemplateRepository
from resources import strings
from models.domain.request_action import RequestAction
from models.domain.resource import ResourceType
from db.repositories.resources import ResourceRepository
from models.domain.authentication import User
from core import config
from db.repositories.base import BaseRepository

from db.errors import EntityDoesNotExist
from models.domain.operation import Operation, OperationStep, Status

WORKSPACE_LEASE_EXPIRY_SECONDS = 300.0


def extract_workspace_id_from_resource_path(resource_path: str) -> Optional[str]:
    if resource_path and resource_path.startswith("/workspaces/"):
        parts = resource_path.split("/")
        if len(parts) > 2:
            return parts[2]
    return None


class OperationRepository(BaseRepository):
    @classmethod
    async def create(cls):
        cls = OperationRepository()
        await super().create(config.STATE_STORE_OPERATIONS_CONTAINER)
        return cls

    async def save_item(self, item: Operation):
        item_dict = item.model_dump(exclude={"etag"})
        item_dict.pop("_etag", None)
        response = await self.container.create_item(body=item_dict)
        if isinstance(response, dict) and "_etag" in response:
            new_etag = response["_etag"]
            item.etag = new_etag.replace('\"', '') if isinstance(new_etag, str) else new_etag

    async def get_active_operations_for_resource(self, resource_id: str) -> List[Operation]:
        query = self.operations_query() + f' c.resourceId = "{resource_id}" AND NOT ARRAY_CONTAINS(["deployed", "deleted", "updated", "invoking_action_failed"], c.status)'
        operations = await self.query(query=query)
        return [TypeAdapter(Operation).validate_python(op) for op in operations]

    async def get_last_operation_for_resource(self, resource_id: str) -> Operation:
        query = self.operations_query() + f' c.resourceId = "{resource_id}" ORDER BY c.createdWhen DESC OFFSET 0 LIMIT 1'
        operations = await self.query(query=query)
        if not operations:
            raise EntityDoesNotExist
        return TypeAdapter(Operation).validate_python(operations[0])

    async def update_item(self, item: Operation, etag: Optional[str] = None) -> Operation:
        etag_to_match = etag or getattr(item, "etag", None)
        item_dict = item.model_dump(exclude={"etag"})
        item_dict.pop("_etag", None)
        if etag_to_match:
            response = await self.container.replace_item(
                item=item.id,
                body=item_dict,
                etag=etag_to_match,
                match_condition=MatchConditions.IfNotModified
            )
            if isinstance(response, dict) and "_etag" in response:
                new_etag = response["_etag"]
                item.etag = new_etag.replace('\"', '') if isinstance(new_etag, str) else new_etag
        else:
            response = await self.container.upsert_item(body=item_dict)
            if isinstance(response, dict) and "_etag" in response:
                new_etag = response["_etag"]
                item.etag = new_etag.replace('\"', '') if isinstance(new_etag, str) else new_etag

        active_statuses = (
            Status.AwaitingAction, Status.InvokingAction, Status.AwaitingDeployment,
            Status.Deploying, Status.AwaitingDeletion, Status.Deleting,
            Status.AwaitingUpdate, Status.Updating, Status.PipelineRunning
        )
        if item.status not in active_statuses:
            target_workspace_id = extract_workspace_id_from_resource_path(item.resourcePath)
            if target_workspace_id:
                await self.release_workspace_lease(target_workspace_id, item.id)

        return item

    async def acquire_workspace_lease(self, workspace_id: str, operation_id: str) -> bool:
        if not hasattr(self, "_container") or self._container is None:
            return True

        if hasattr(self, "resource_has_active_operation"):
            check = self.resource_has_active_operation(workspace_id)
            if hasattr(check, "__await__"):
                is_active = await check
            else:
                is_active = check
            if is_active is True:
                raise HTTPException(status_code=http_status.HTTP_409_CONFLICT, detail=strings.WORKSPACE_HAS_ACTIVE_OPERATION)

        lease_id = f"lease_{workspace_id}"
        max_attempts = 3

        for attempt in range(max_attempts):
            timestamp = self.get_timestamp()
            lease_body = {
                "id": lease_id,
                "workspaceId": workspace_id,
                "operationId": operation_id,
                "createdWhen": timestamp,
            }

            try:
                create_call = self.container.create_item(body=lease_body)
                if hasattr(create_call, "__await__"):
                    await create_call
                return True
            except (CosmosResourceExistsError, ResourceExistsError):
                try:
                    read_call = self.read_item_by_id(lease_id)
                    existing_lease = await read_call if hasattr(read_call, "__await__") else read_call
                except (CosmosResourceNotFoundError, ResourceNotFoundError, EntityDoesNotExist):
                    # The lease was released between create_item conflict and read_item_by_id; retry
                    if attempt < max_attempts - 1:
                        continue
                    raise

                if not isinstance(existing_lease, dict):
                    return True

                current_op_id = existing_lease.get("operationId")
                if current_op_id == operation_id:
                    return True

                lease_created = existing_lease.get("createdWhen", 0.0)

                if current_op_id:
                    try:
                        op_call = self.get_operation_by_id(current_op_id)
                        existing_op = await op_call if hasattr(op_call, "__await__") else op_call
                        terminal_statuses = {
                            Status.Deployed,
                            Status.DeploymentFailed,
                            Status.Deleted,
                            Status.DeletingFailed,
                            Status.Updated,
                            Status.UpdatingFailed,
                            Status.ActionSucceeded,
                            Status.ActionFailed,
                        }
                        if existing_op and getattr(existing_op, "status", None) not in terminal_statuses:
                            raise HTTPException(status_code=http_status.HTTP_409_CONFLICT, detail=strings.WORKSPACE_HAS_ACTIVE_OPERATION)
                    except (EntityDoesNotExist, CosmosResourceNotFoundError):
                        # Operation doc not written yet (still constructing cascade/operation).
                        # Safely reclaim orphaned leases after a bounded interval (WORKSPACE_LEASE_EXPIRY_SECONDS).
                        if timestamp - lease_created < WORKSPACE_LEASE_EXPIRY_SECONDS:
                            raise HTTPException(status_code=http_status.HTTP_409_CONFLICT, detail=strings.WORKSPACE_HAS_ACTIVE_OPERATION)

                etag = existing_lease.get("_etag") if isinstance(existing_lease, dict) else None
                try:
                    if etag:
                        rep_call = self.container.replace_item(
                            item=lease_id,
                            body=lease_body,
                            etag=etag,
                            match_condition=MatchConditions.IfNotModified
                        )
                        if hasattr(rep_call, "__await__"):
                            await rep_call
                    else:
                        up_call = self.container.upsert_item(body=lease_body)
                        if hasattr(up_call, "__await__"):
                            await up_call
                    return True
                except (CosmosAccessConditionFailedError, ResourceExistsError):
                    if attempt < max_attempts - 1:
                        continue
                    raise HTTPException(status_code=http_status.HTTP_409_CONFLICT, detail=strings.WORKSPACE_HAS_ACTIVE_OPERATION)

    async def release_workspace_lease(self, workspace_id: str, operation_id: Optional[str] = None) -> None:
        if not hasattr(self, "_container") or self._container is None:
            return
        lease_id = f"lease_{workspace_id}"
        try:
            read_call = self.read_item_by_id(lease_id)
            existing_lease = await read_call if hasattr(read_call, "__await__") else read_call
            if isinstance(existing_lease, dict) and (not operation_id or existing_lease.get("operationId") == operation_id):
                del_call = self.delete_item(lease_id)
                if hasattr(del_call, "__await__"):
                    await del_call
        except Exception:
            pass

    @staticmethod
    def operations_query():
        return 'SELECT * FROM c WHERE'

    @staticmethod
    def get_timestamp() -> float:
        return datetime.now(UTC).timestamp()

    @staticmethod
    def create_operation_id() -> str:
        return str(uuid.uuid4())

    def create_main_step(self, resource_template: dict, action: str, resource_id: str, status: Status, message: str) -> OperationStep:
        return OperationStep(
            id=str(uuid.uuid4()),
            templateStepId="main",
            stepTitle=f"Main step for {resource_id}",
            resourceId=resource_id,
            resourceTemplateName=resource_template["name"],
            resourceType=resource_template["resourceType"],
            resourceAction=action,
            sourceTemplateResourceId=resource_id,
            status=status,
            message=message,
            updatedWhen=self.get_timestamp())

    async def create_operation_item(self, resource_id: str, resource_list: List, action: str, resource_path: str, resource_version: int, user: User, resource_repo: ResourceRepository, resource_template_repo: ResourceTemplateRepository, operation_id: Optional[str] = None) -> Operation:
        if not operation_id:
            operation_id = self.create_operation_id()

        target_workspace_id = extract_workspace_id_from_resource_path(resource_path)
        if target_workspace_id:
            await self.acquire_workspace_lease(target_workspace_id, operation_id)

        try:
            # get the right "awaiting" message based on the action
            status, message = self.get_initial_status(action)
            all_steps = []
            for resource in resource_list:
                name = resource["templateName"]
                version = resource["templateVersion"]
                resource_type = ResourceType(resource["resourceType"])
                primary_parent_service_name = None
                if resource_type == ResourceType.UserResource:
                    primary_parent_workspace_service = await resource_repo.get_resource_by_id(resource["parentWorkspaceServiceId"])
                    primary_parent_service_name = primary_parent_workspace_service.templateName
                resource_template = await resource_template_repo.get_template_by_name_and_version(name, version, resource_type, primary_parent_service_name)
                resource_template_dict = resource_template.model_dump(exclude_none=True)
                # if the template has a pipeline defined for this action, copy over all the steps to the ops document
                steps = await self.build_step_list(
                    steps=[],
                    resource_template_dict=resource_template_dict,
                    action=action,
                    resource_repo=resource_repo,
                    resource_id=resource["id"],
                    status=status,
                    message=message,
                    is_cascade_operation=resource["id"] != resource_id
                )

                # if no pipeline is defined for this action, create a main step only
                if len(steps) == 0:
                    all_steps.append(self.create_main_step(resource_template=resource_template_dict, action=action, resource_id=resource["id"], status=status, message=message))
                else:
                    all_steps.extend(steps)

            timestamp = self.get_timestamp()
            operation = Operation(
                id=operation_id,
                resourceId=resource_id,
                resourcePath=resource_path,
                resourceVersion=resource_version,
                status=status,
                createdWhen=timestamp,
                updatedWhen=timestamp,
                action=action,
                message=message,
                user=user.model_dump(),
                steps=all_steps
            )

            await self.save_item(operation)
            return operation
        except Exception:
            if target_workspace_id:
                await self.release_workspace_lease(target_workspace_id, operation_id)
            raise

    async def build_step_list(self, steps: List[OperationStep], resource_template_dict: dict, action: str, resource_repo: ResourceRepository, resource_id: str, status: Status, message: str, is_cascade_operation: bool = False):
        if "pipeline" in resource_template_dict and resource_template_dict["pipeline"] is not None:
            if action in resource_template_dict["pipeline"] and resource_template_dict["pipeline"][action] is not None:
                for step in resource_template_dict["pipeline"][action]:
                    if is_cascade_operation and step["stepId"] == strings.ADDRESS_SPACE_CLEANUP_STEP_ID:
                        continue
                    if step["stepId"] == "main":
                        steps.append(self.create_main_step(resource_template=resource_template_dict, action=action, resource_id=resource_id, status=status, message=message))
                    else:
                        resource_for_step = None

                        # if it's a shared service, should be a singleton across the TRE, get it by template name
                        if step["resourceType"] == ResourceType.SharedService:
                            resource_for_step = await resource_repo.get_active_resource_by_template_name(step["resourceTemplateName"])

                        # if it's a workspace, find the parent workspace of where we are
                        if step["resourceType"] == ResourceType.Workspace:
                            primary_resource = await resource_repo.get_resource_by_id(uuid.UUID(resource_id))
                            if primary_resource.resourceType == ResourceType.SharedService or primary_resource.resourceType == ResourceType.Workspace:
                                raise Exception("You can only reference a workspace from a workspace service or user resource")
                            resource_for_step = await resource_repo.get_resource_by_id(uuid.UUID(primary_resource.workspaceId))

                        # if it's a workspace service, we must be a user-resource - find the parent
                        if step["resourceType"] == ResourceType.WorkspaceService:
                            primary_resource = await resource_repo.get_resource_by_id(uuid.UUID(resource_id))
                            if primary_resource.resourceType != ResourceType.UserResource:
                                raise Exception("Only user resources can update their parent workspace services")
                            resource_for_step = await resource_repo.get_resource_by_id(uuid.UUID(primary_resource.parentWorkspaceServiceId))

                        if resource_for_step is None:
                            raise Exception(f"Error finding resource to update, triggered by resource ID {resource_id}")

                        resource_for_step_status, resource_for_step_message = self.get_initial_status(step["resourceAction"])

                        steps.append(OperationStep(
                            id=str(uuid.uuid4()),
                            templateStepId=step["stepId"],
                            stepTitle=step["stepTitle"],
                            resourceId=resource_for_step.id,
                            resourceTemplateName=resource_for_step.templateName,
                            resourceType=resource_for_step.resourceType,
                            resourceAction=step["resourceAction"],
                            status=resource_for_step_status,
                            message=resource_for_step_message,
                            updatedWhen=self.get_timestamp(),
                            sourceTemplateResourceId=resource_id
                        ))
        return steps

    def get_initial_status(self, action: RequestAction):
        status = Status.AwaitingAction
        message = strings.RESOURCE_STATUS_AWAITING_ACTION_MESSAGE

        if action == RequestAction.Install:
            status = Status.AwaitingDeployment
            message = strings.RESOURCE_STATUS_AWAITING_DEPLOYMENT_MESSAGE
        elif action == RequestAction.UnInstall:
            status = Status.AwaitingDeletion
            message = strings.RESOURCE_STATUS_AWAITING_DELETION_MESSAGE
        elif action == RequestAction.Upgrade:
            status = Status.AwaitingUpdate
            message = strings.RESOURCE_STATUS_AWAITING_UPDATE_MESSAGE

        return status, message

    async def update_operation_status(self, operation_id: str, status: Status, message: str) -> Operation:
        operation = await self.get_operation_by_id(operation_id)

        operation.status = status
        operation.message = message
        operation.updatedWhen = datetime.now(UTC).timestamp()

        await self.update_item(operation)
        return operation

    async def get_operation_by_id(self, operation_id: str) -> Operation:
        query = self.operations_query() + f' c.id = "{operation_id}"'
        operation = await self.query(query=query)
        if not operation:
            raise EntityDoesNotExist
        return TypeAdapter(Operation).validate_python(operation[0])

    async def get_my_operations(self, user_id: str) -> List[Operation]:
        query = self.operations_query() + f' c.user.id = "{user_id}" AND c.status IN ("{Status.AwaitingAction}", "{Status.InvokingAction}", "{Status.AwaitingDeployment}", "{Status.Deploying}", "{Status.AwaitingDeletion}", "{Status.Deleting}", "{Status.AwaitingUpdate}", "{Status.Updating}", "{Status.PipelineRunning}") ORDER BY c.createdWhen ASC'
        operations = await self.query(query=query)
        return TypeAdapter(List[Operation]).validate_python(operations)

    async def get_operations_by_resource_id(self, resource_id: str) -> List[Operation]:
        query = self.operations_query() + f' c.resourceId = "{resource_id}"'
        operations = await self.query(query=query)
        return TypeAdapter(List[Operation]).validate_python(operations)

    async def resource_has_deployed_operation(self, resource_id: str) -> bool:
        query = self.operations_query() + f' c.resourceId = "{resource_id}" AND ((c.action = "{RequestAction.Install}" AND c.status = "{Status.Deployed}") OR (c.action = "{RequestAction.Upgrade}" AND c.status = "{Status.Updated}"))'
        operations = await self.query(query=query)
        return len(operations) > 0

    async def resource_has_active_operation(self, resource_id: str) -> bool:
        # Guard against injection; resource_id should always be a valid UUID string
        try:
            uuid.UUID(resource_id)
        except ValueError:
            return False
        active_statuses = (
            Status.AwaitingAction, Status.InvokingAction, Status.AwaitingDeployment,
            Status.Deploying, Status.AwaitingDeletion, Status.Deleting,
            Status.AwaitingUpdate, Status.Updating, Status.PipelineRunning
        )
        status_filter = ", ".join(f'"{s}"' for s in active_statuses)
        query = (
            self.operations_query()
            + f' (c.resourceId = "{resource_id}"'
            + f' OR ARRAY_CONTAINS(c.steps, {{"resourceId": "{resource_id}"}}, true)'
            # Include any operation whose resource path contains this resource id — this catches
            # cascading operations on all descendant resources (workspace services AND user resources).
            # The previous NOT CONTAINS(c.resourcePath, "/user-resources/") exclusion meant that
            # active user-resource operations were invisible when checking a parent workspace or
            # workspace-service, allowing duplicate cascading pipelines to start.
            + f' OR CONTAINS(c.resourcePath, "{resource_id}"))'
            + f' AND c.status IN ({status_filter})'
        )
        operations = await self.query(query=query)
        return len(operations) > 0
