from datetime import datetime
import uuid
from typing import List

from azure.cosmos import CosmosClient
from pydantic import parse_obj_as
from db.repositories.resources import ResourceRepository
from models.domain.resource_template import ResourceTemplate
from models.domain.authentication import User
from core import config
from db.repositories.base import BaseRepository

from db.errors import EntityDoesNotExist
from models.domain.operation import Operation, OperationStep, Status


class OperationRepository(BaseRepository):
    def __init__(self, client: CosmosClient):
        super().__init__(client, config.STATE_STORE_OPERATIONS_CONTAINER)

    @staticmethod
    def operations_query():
        return 'SELECT * FROM c WHERE'

    @staticmethod
    def get_timestamp() -> float:
        return datetime.utcnow().timestamp()

    @staticmethod
    def create_operation_id() -> str:
        return str(uuid.uuid4())

    def create_main_step(self, resource_template: dict, action: str, resource_id: str, status: Status, message: str) -> OperationStep:
        return OperationStep(
            stepId="main",
            stepTitle=f"Main step for {resource_id}",
            resourceId=resource_id,
            resourceTemplateName=resource_template["name"],
            resourceType=resource_template["resourceType"],
            resourceAction=action,
            status=status,
            message=message,
            updatedWhen=self.get_timestamp())

    def create_operation_item(self, resource_id: str, status: Status, action: str, message: str, resource_path: str, resource_version: int, user: User, resource_template: ResourceTemplate, resource_repo: ResourceRepository) -> Operation:
        operation_id = self.create_operation_id()
        resource_template_dict = resource_template.dict(exclude_none=True)

        # if the template has a pipeline defined for this action, copy over all the steps to the ops document
        steps = self.build_step_list(
            steps=[],
            resource_template_dict=resource_template_dict,
            action=action,
            resource_repo=resource_repo,
            resource_id=resource_id,
            status=status,
            message=message
        )

        # if no pipeline is defined for this action, create a main step only
        if len(steps) == 0:
            steps.append(self.create_main_step(resource_template=resource_template_dict, action=action, resource_id=resource_id, status=status, message=message))

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
            user=user,
            steps=steps
        )

        self.save_item(operation)
        return operation

    def build_step_list(self, steps: List[OperationStep], resource_template_dict: dict, action: str, resource_repo: ResourceRepository, resource_id: str, status: Status, message: str):
        if "pipeline" in resource_template_dict and resource_template_dict["pipeline"] is not None:
            if action in resource_template_dict["pipeline"] and resource_template_dict["pipeline"][action] is not None:
                for step in resource_template_dict["pipeline"][action]:
                    if step["stepId"] == "main":
                        steps.append(self.create_main_step(resource_template=resource_template_dict, action=action, resource_id=resource_id, status=status, message=message))
                    else:
                        resource_for_step = resource_repo.get_resource_by_template_name(step["resourceTemplateName"])
                        steps.append(OperationStep(
                            stepId=step["stepId"],
                            stepTitle=step["stepTitle"],
                            resourceId=resource_for_step.id,
                            resourceTemplateName=step["resourceTemplateName"],
                            resourceType=step["resourceType"],
                            resourceAction=step["resourceAction"],
                            updatedWhen=self.get_timestamp()
                        ))
        return steps

    def update_operation_status(self, operation_id: str, status: Status, message: str) -> Operation:
        operation = self.get_operation_by_id(operation_id)

        operation.status = status
        operation.message = message
        operation.updatedWhen = datetime.utcnow().timestamp()

        self.update_item(operation)
        return operation

    def get_operation_by_id(self, operation_id: str) -> Operation:
        """
        returns a single operation doc
        """
        query = self.operations_query() + f' c.id = "{operation_id}"'
        operation = self.query(query=query)
        if not operation:
            raise EntityDoesNotExist
        return parse_obj_as(Operation, operation[0])

    def get_operations_by_resource_id(self, resource_id: str) -> List[Operation]:
        """
        returns a list of operations for this resource
        """
        query = self.operations_query() + f' c.resourceId = "{resource_id}"'
        operations = self.query(query=query)
        return parse_obj_as(List[Operation], operations)

    def resource_has_deployed_operation(self, resource_id: str) -> bool:
        """
        checks whether this resource has a successful "deployed" operation
        """
        query = self.operations_query() + f' c.resourceId = "{resource_id}" AND c.status = "{Status.Deployed}"'
        operations = self.query(query=query)
        return len(operations) > 0
