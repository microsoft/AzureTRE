import { User } from "./user";

export interface Operation {
    resourceId: string,
    resourcePath: string,
    resourceVersion: number,
    status: string,
    action: string,
    message: string,
    createdWhen: number,
    updatedWhen: number,
    user: User,
    steps?: Array<OperationStep>
}

export interface OperationStep {
    stepId: string,
    stepTitle: string,
    resourceId: string,
    resourceTemplateName: string,
    resourceType: ResourceType,
    resourceAction: string,
    status: string,
    message: string,
    updatedWhen: number
}

export const completedStates = [
    "deployed",
    "deleted",
    "failed",
    "deleting_failed",
    "action_succeeded",
    "action_failed",
    "pipeline_failed",
    "pipeline_succeeded"
]

export const inProgressStates = [
    "not_deployed",
    "deploying",
    "deleting",
    "invoking_action",
    "pipeline_deploying"
]

export const failedStates = [
    "failed",
    "deleting_failed",
    "action_failed",
    "pipeline_failed",
]
