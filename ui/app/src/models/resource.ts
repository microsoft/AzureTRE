import { ResourceType } from "./resourceType";
import { User } from "./user";

export interface Resource {
    id: string,
    isActive: boolean,
    isEnabled: boolean,
    resourcePath: string,
    resourceVersion: number,
    resourceType: ResourceType
    templateName: string,
    templateVersion: string,
    updatedWhen: number,
    user: User,
    history: Array<HistoryItem>,
    _etag: string,
    properties: any
}

export interface HistoryItem {
    isEnabled: boolean,
    resourceVersion: number,
    updatedWhen: number,
    user: User,
    properties: any
}