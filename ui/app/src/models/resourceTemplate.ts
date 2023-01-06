import { ResourceType } from "./resourceType";

export interface ResourceTemplate {
  id: string,
  name: string,
  type: string,
  description: string,
  version: string,
  title: string,
  resourceType: ResourceType,
  current: boolean,
  properties: any,
  allOf?: Array<any>,
  system_properties: any,
  actions: Array<TemplateAction>,
  customActions: Array<TemplateAction>,
  required: Array<string>,
  uiSchema: any,
  pipeline: any
}

export const sanitiseTemplateForRJSF = (template: ResourceTemplate) => {
  if (template.properties) {
    Object.keys(template.properties).forEach((key: string) => {
      Object.keys(template.properties[key]).forEach((name: string) => {
        if (template.properties[key][name] === null) {
          delete template.properties[key][name]
        }
      });
    });
  }

  const sanitised = {
    name: template.name,
    type: template.type,
    description: template.description,
    title: template.title,
    properties: template.properties,
    allOf: template.allOf,
    required: template.required,
    uiSchema: template.uiSchema
  }

  if (!sanitised.allOf) delete sanitised.allOf;

  return sanitised;
};

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
};
