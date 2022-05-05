import { ResourceType } from "./resourceType";
import { User } from "./user";

export interface Resource {
    id: String,
    isActive: boolean,
    isEnabled: boolean,
    resourcePath: String,
    resourceVersion: number,
    resourceType: ResourceType
    templateName: String,
    templateVersion: String,
    updatedWhen: number,
    user: User,
    history: Array<HistoryItem>,
    _etag: String,
    properties: any
}

interface HistoryItem {
    isEnabled: boolean,
    resourceVersion: number,
    updatedWhen: number,
    user: User,
    properties: any
}