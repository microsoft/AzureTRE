import { Operation } from "./operation";
import { ResourceType } from "./resourceType";
import { User } from "./user";

export interface Resource {
    id: string,
    isEnabled: boolean,
    resourcePath: string,
    resourceVersion: number,
    resourceType: ResourceType
    templateName: string,
    templateVersion: string,
    deploymentStatus: string,
    updatedWhen: number,
    user: User,
    history: Array<HistoryItem>,
    _etag: string,
    properties: any,
    azureStatus?: any
}

export interface HistoryItem {
    isEnabled: boolean,
    resourceVersion: number,
    updatedWhen: number,
    user: User,
    properties: any
}

export enum ComponentAction {
    None,
    Reload,
    Remove,
    Lock
}

export interface ResourceUpdate {
    operation: Operation,
    componentAction: ComponentAction
}

export enum VMPowerStates {
  Running = "VM running",
  Starting = "VM starting",
  Stopping = "VM stopping",
  Stopped = "VM stopped",
  Deallocating = "VM deallocating",
  Deallocated = "VM deallocated"
}

export const getResourceFromResult = (r: any) => {
    if (r['userResource']) return r.userResource;
    if (r['workspaceService']) return r.workspaceService;
    if (r['workspace']) return r.workspace;
    if (r['sharedService']) return r.sharedService;
}
