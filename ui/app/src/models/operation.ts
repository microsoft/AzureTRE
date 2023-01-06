import { ResourceType } from "./resourceType";
import { User } from "./user";

export interface Operation {
    id: string,
    resourceId: string,
    resourcePath: string,
    resourceVersion: number,
    status: string,
    action: string,
    message: string,
    createdWhen: number,
    updatedWhen: number,
    user: User,
    steps?: Array<OperationStep>,
    dismiss?: Boolean // UI-only prop, not fed from the API
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

export const awaitingStates = [
  "awaiting_deployment",
  "awaiting_update",
  "awaiting_deletion",
  "awaiting_action"
]

export const successStates = [
  "deployed",
  "updated",
  "deleted",
  "action_succeeded"
]

export const failedStates = [
  "deployment_failed",
  "deleting_failed",
  "updating_failed",
  "action_failed",
]

export const completedStates = [
  ...failedStates,
  ...successStates
]

export const inProgressStates = [
  ...awaitingStates,
  "deploying",
  "updating",
  "deleting",
  "invoking_action",
  "pipeline_running"
]

export const actionsDisabledStates = [
  ...inProgressStates,
  "deployment_failed",
  "failed"
]
