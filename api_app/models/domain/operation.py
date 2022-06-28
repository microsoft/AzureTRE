from enum import Enum
from typing import List, Optional

from pydantic import Field
from pydantic.types import UUID4

from models.domain.azuretremodel import AzureTREModel
from models.domain.resource import Output, ResourceType
from resources import strings


class Status(str, Enum):
    """
    Operation status
    """
    NotDeployed = strings.RESOURCE_STATUS_NOT_DEPLOYED  # Initial status of a resource
    Deploying = strings.RESOURCE_STATUS_DEPLOYING
    Deployed = strings.RESOURCE_STATUS_DEPLOYED
    Failed = strings.RESOURCE_STATUS_FAILED
    Deleting = strings.RESOURCE_STATUS_DELETING
    Deleted = strings.RESOURCE_STATUS_DELETED
    DeletingFailed = strings.RESOURCE_STATUS_DELETING_FAILED
    InvokingAction = strings.RESOURCE_ACTION_STATUS_INVOKING
    ActionSucceeded = strings.RESOURCE_ACTION_STATUS_SUCCEEDED
    ActionFailed = strings.RESOURCE_ACTION_STATUS_FAILED
    PipelineDeploying = strings.RESOURCE_ACTION_STATUS_PIPELINE_DEPLOYING
    PipelineFailed = strings.RESOURCE_ACTION_STATUS_PIPELINE_FAILED
    PipelineSucceeded = strings.RESOURCE_ACTION_STATUS_PIPELINE_SUCCEEDED


class OperationStep(AzureTREModel):
    """
    Model to define a step in an operation. Each step references either a secondary resource or the primary resource (stepId=main)
    The steps are built up front as the operation is created from the initial user request.
    As each step completes, the next one is processed.
    """
    stepId: str = Field(title="stepId", description="Unique id identifying the step")
    stepTitle: Optional[str] = Field(title="stepTitle", description="Human readable title of what the step is for")
    resourceId: Optional[str] = Field(title="resourceId", description="Id of the resource to update")
    resourceTemplateName: Optional[str] = Field("", title="resourceTemplateName", description="Name of the template for the resource under change")
    resourceType: Optional[ResourceType] = Field(title="resourceType", description="Type of resource under change")
    resourceAction: Optional[str] = Field(title="resourceAction", description="Action - install / upgrade / uninstall etc")
    status: Optional[Status] = Field(Status.NotDeployed, title="Operation step status")
    message: Optional[str] = Field("", title="Additional operation step status information")
    updatedWhen: Optional[float] = Field("", title="POSIX Timestamp for When the operation step was updated")

    def is_success(self) -> bool:
        return self.status in (
            Status.ActionSucceeded,
            Status.Deployed,
            Status.Deleted
        )

    def is_failure(self) -> bool:
        return self.status in (
            Status.ActionFailed,
            Status.DeletingFailed,
            Status.Failed
        )

    def is_action(self) -> bool:
        return self.status in (
            Status.ActionSucceeded,
            Status.ActionFailed,
            Status.InvokingAction
        )


class Operation(AzureTREModel):
    """
    Operation model
    """
    id: str = Field(title="Id", description="GUID identifying the operation")
    resourceId: str = Field(title="resourceId", description="GUID identifying the resource")
    resourcePath: str = Field(title="resourcePath", description="Path of the resource undergoing change, i.e. '/workspaces/guid/workspace-services/guid/'")
    resourceVersion: int = Field(0, title="resourceVersion", description="Version of the resource this operation relates to")
    status: Status = Field(Status.NotDeployed, title="Operation status")
    action: str = Field(title="action", description="Name of the action being performed on the resource, i.e. install, uninstall, start")
    message: str = Field("", title="Additional operation status information")
    createdWhen: float = Field("", title="POSIX Timestamp for when the operation was submitted")
    updatedWhen: float = Field("", title="POSIX Timestamp for When the operation was updated")
    user: dict = {}
    steps: Optional[List[OperationStep]] = Field(None, title="Operation Steps")


class DeploymentStatusUpdateMessage(AzureTREModel):
    """
    Model for service bus message flowing back to API to update status in DB
    """
    operationId: UUID4 = Field(title="", description="")
    stepId: str = Field(title="", description="")
    id: UUID4 = Field(title="", description="")
    status: Status = Field(title="", description="")
    message: str = Field(title="", description="")
    outputs: List[Output] = Field(title="", description="", default=[])
