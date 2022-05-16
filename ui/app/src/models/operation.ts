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
    steps?: Array<OperationStep>
}

interface OperationStep {
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