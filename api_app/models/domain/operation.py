from enum import StrEnum
from typing import List, Optional

from pydantic import Field
from pydantic.types import UUID4

from models.domain.azuretremodel import AzureTREModel
from models.domain.resource import Output, ResourceType
from resources import strings


class Status(StrEnum):
    """
    Operation status
    """
    AwaitingDeployment = strings.RESOURCE_STATUS_AWAITING_DEPLOYMENT
    Deploying = strings.RESOURCE_STATUS_DEPLOYING
    Deployed = strings.RESOURCE_STATUS_DEPLOYED
    DeploymentFailed = strings.RESOURCE_STATUS_DEPLOYMENT_FAILED

    AwaitingUpdate = strings.RESOURCE_STATUS_AWAITING_UPDATE
    Updating = strings.RESOURCE_STATUS_UPDATING
    Updated = strings.RESOURCE_STATUS_UPDATED
    UpdatingFailed = strings.RESOURCE_STATUS_UPDATING_FAILED

    AwaitingDeletion = strings.RESOURCE_STATUS_AWAITING_DELETION
    Deleting = strings.RESOURCE_STATUS_DELETING
    Deleted = strings.RESOURCE_STATUS_DELETED
    DeletingFailed = strings.RESOURCE_STATUS_DELETING_FAILED

    AwaitingAction = strings.RESOURCE_STATUS_AWAITING_ACTION
    InvokingAction = strings.RESOURCE_ACTION_STATUS_INVOKING
    ActionSucceeded = strings.RESOURCE_ACTION_STATUS_SUCCEEDED
    ActionFailed = strings.RESOURCE_ACTION_STATUS_FAILED

    PipelineRunning = strings.RESOURCE_ACTION_STATUS_PIPELINE_RUNNING  # set whilst a resource in a pipeline is running, as each step will have its own status


class OperationStep(AzureTREModel):
    """
    Model to define a step in an operation. Each step references either a secondary resource or the primary resource (stepId=main)
    The steps are built up front as the operation is created from the initial user request.
    As each step completes, the next one is processed.
    """
    id: str = Field(title="Id", description="Unique id identifying the step")
    templateStepId: str = Field(title="templateStepId", description="Unique id identifying the step")
    stepTitle: Optional[str] = Field(title="stepTitle", description="Human readable title of what the step is for")
    resourceId: Optional[str] = Field(title="resourceId", description="Id of the resource to update")
    resourceTemplateName: Optional[str] = Field("", title="resourceTemplateName", description="Name of the template for the resource under change")
    resourceType: Optional[ResourceType] = Field(title="resourceType", description="Type of resource under change")
    resourceAction: Optional[str] = Field(title="resourceAction", description="Action - install / upgrade / uninstall etc")
    status: Optional[Status] = Field(None, title="Operation step status")
    message: Optional[str] = Field("", title="Additional operation step status information")
    updatedWhen: Optional[float] = Field("", title="POSIX Timestamp for When the operation step was updated")
    # An example for this property will be if we have a step that is responsible for updating the firewall, and its origin was the guacamole workspace service, the id here will be the guacamole id
    sourceTemplateResourceId: Optional[str] = Field(title="sourceTemplateResourceId", description="Id of the parent of the resource to update")

    def is_success(self) -> bool:
        return self.status in (
            Status.ActionSucceeded,
            Status.Deployed,
            Status.Deleted,
            Status.Updated
        )

    def is_failure(self) -> bool:
        return self.status in (
            Status.ActionFailed,
            Status.DeletingFailed,
            Status.DeploymentFailed,
            Status.UpdatingFailed
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
    status: Status = Field(None, title="Operation status")
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
