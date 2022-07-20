import { ResourceType } from "./resourceType";

export interface ResourceTemplate {
    id: string,
    name: string,
    version: string,
    title: string,
    resourceType: ResourceType,
    current: boolean,
    properties: any,
    system_properties: any,
    actions: Array<TemplateAction>,
    customActions: Array<TemplateAction>,
    uiSchema: any
}

export interface TemplateAction {
    name: string,
    description: string
}

// make a sensible guess at an icon
export const getActionIcon = (actionName: string) => {
    switch(actionName.toLowerCase()){
        case 'start':
            return 'Play';
        case 'stop':
            return 'Stop';
        default:
            return 'Asterisk'
    }
}
