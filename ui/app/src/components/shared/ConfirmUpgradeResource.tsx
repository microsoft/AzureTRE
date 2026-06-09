import {
  Dialog,
  DialogFooter,
  PrimaryButton,
  DialogType,
  Spinner,
  Dropdown,
  MessageBar,
  MessageBarType,
  Icon,
  Stack,
} from "@fluentui/react";
import React, { useContext, useState, useEffect, useRef } from "react";
import { AvailableUpgrade, Resource } from "../../models/resource";
import { ApiEndpoint } from "../../models/apiEndpoints";
import { WorkspaceService } from "../../models/workspaceService";
import {
  HttpMethod,
  ResultType,
  useAuthApiCall,
} from "../../hooks/useAuthApiCall";
import { WorkspaceContext } from "../../contexts/WorkspaceContext";
import { ResourceType } from "../../models/resourceType";
import { APIError } from "../../models/exceptions";
import { LoadingState } from "../../models/loadingState";
import { ExceptionLayout } from "./ExceptionLayout";
import { useAppDispatch } from "../../hooks/customReduxHooks";
import { addUpdateOperation } from "../shared/notifications/operationsSlice";
import Form from "@rjsf/fluent-ui";
import validator from "@rjsf/validator-ajv8";

interface ConfirmUpgradeProps {
  resource: Resource;
  onDismiss: () => void;
}

// Utility to get all property keys from template schema's properties object recursively, flattening nested if needed
const getAllPropertyKeys = (properties: any, prefix = ""): string[] => {
  if (!properties) return [];
  let keys: string[] = [];
  for (const [key, value] of Object.entries(properties)) {
    if (value && typeof value === "object" && 'properties' in value) {
      // recur for nested properties
      keys = keys.concat(getAllPropertyKeys(value["properties"], prefix + key + "."));
    } else {
      keys.push(prefix + key);
    }
  }
  return keys;
};

// Utility to get a nested value from an object using a dotted path (e.g. "parent.child")
const getNestedValue = (obj: any, path: string): any => {
  const parts = path.split('.');
  let current = obj;
  for (const part of parts) {
    if (current === null || current === undefined) return undefined;
    current = current[part];
  }
  return current;
};

// Utility to set a nested value in an object using a dotted path (e.g. "parent.sibling")
const setNestedValue = (obj: any, path: string, value: any): void => {
  const parts = path.split('.');
  let current = obj;
  for (let i = 0; i < parts.length - 1; i++) {
    const part = parts[i];
    if (!(part in current) || typeof current[part] !== 'object' || current[part] === null) {
      current[part] = {};
    }
    current = current[part];
  }
  current[parts[parts.length - 1]] = value;
};

// Utility to get schema property from properties object using a dotted path
const getSchemaProperty = (properties: any, path: string): any => {
  const parts = path.split('.');
  let current = properties;
  for (let i = 0; i < parts.length; i++) {
    const part = parts[i];
    if (!current || !current[part]) return null;
    if (i === parts.length - 1) {
      return current[part];
    }
    current = current[part].properties;
  }
  return null;
};

// Utility to get nested uiSchema object using a dotted path
const getNestedUiSchema = (uiSchema: any, path: string): any => {
  const parts = path.split('.');
  let current = uiSchema;
  for (const part of parts) {
    if (current === null || current === undefined) return undefined;
    current = current[part];
  }
  return current;
};

// Utility to check if a nested property (dotted path) is required in the schema given the current form state
const isPropertyRequiredInState = (
  propertiesSchema: any,
  rootRequired: string[] | undefined,
  path: string,
  state: any
): boolean => {
  const parts = path.split('.');
  let currentSchema = propertiesSchema;
  let currentRequired = rootRequired;
  let currentState = state;

  for (let i = 0; i < parts.length; i++) {
    const part = parts[i];

    // Is the current part required at this level?
    const isPartRequired = currentRequired && currentRequired.includes(part);
    // Is the current part present in the state?
    const isPartPresent = currentState && currentState[part] !== undefined && currentState[part] !== null;

    // A property is only required to be filled if its path of parent objects is required or present.
    // For the final property (the leaf), it must be explicitly required by its parent.
    if (i === parts.length - 1) {
      return !!isPartRequired;
    }

    // For intermediate parents, if it's neither required nor present, then the nested child is not required.
    if (!isPartRequired && !isPartPresent) {
      return false;
    }

    if (!currentSchema || !currentSchema[part] || !currentSchema[part].properties) {
      return false;
    }

    currentRequired = currentSchema[part].required;
    currentSchema = currentSchema[part].properties;
    currentState = currentState ? currentState[part] : undefined;
  }
  return false;
};

// Utility to build a reduced schema with only given keys and their nested schema (depth 1), including required
const buildReducedSchema = (fullSchema: any, keys: string[]): any => {
  if (!fullSchema || !fullSchema.properties) return null;
  const reducedProperties: any = {};
  const required: string[] = [];

  keys.forEach((key) => {
    // Only allow top-level property keys (no nested with dots) for simplicity here
    const topKey = key.split('.')[0];
    if (fullSchema.properties[topKey]) {
      if (!reducedProperties[topKey]) {
        reducedProperties[topKey] = fullSchema.properties[topKey];
        if (fullSchema.required && fullSchema.required.includes(topKey)) {
          required.push(topKey);
        }
      }
    }
  });

  return {
    type: "object",
    properties: reducedProperties,
    required: required.length > 0 ? required : undefined,
  };
};

// Utility to collect direct property keys referenced inside conditional schemas
const collectConditionalKeys = (entry: any): string[] => {
  const keys: string[] = [];
  if (!entry) return keys;
  const collect = (schemaPart: any) => {
    if (schemaPart && schemaPart.properties) {
      keys.push(...Object.keys(schemaPart.properties));
    }
  };
  collect(entry.if);
  collect(entry.then);
  collect(entry.else);
  return [...new Set(keys)];
};

// Extract conditional blocks that reference any of the new properties.
const extractConditionalBlocks = (schema: any, newKeys: string[]) => {
  const conditionalEntries: any[] = [];
  if (!schema) return { allOf: [] };
  const allOf = schema.allOf || [];
  allOf.forEach((entry: any) => {
    if (entry && entry.if) {
      const conditionalKeys = collectConditionalKeys(entry);
      // include entry if any conditionalKey matches a new key (top-level match)
      if (conditionalKeys.some((k) => newKeys.some((nk) => nk.split('.')[0] === k))) {
        conditionalEntries.push(entry);
      }
    }
  });
  return { allOf: conditionalEntries };
};

export const ConfirmUpgradeResource: React.FunctionComponent<
  ConfirmUpgradeProps
> = (props: ConfirmUpgradeProps) => {
  const apiCall = useAuthApiCall();
  const [selectedVersion, setSelectedVersion] = useState("");
  const [apiError, setApiError] = useState<APIError | null>(null);
  const [requestLoadingState, setRequestLoadingState] = useState(
    LoadingState.Ok,
  );
  const workspaceCtx = useContext(WorkspaceContext);
  const dispatch = useAppDispatch();

  const [allNewProperties, setAllNewProperties] = useState<string[]>([]); // All new properties including hidden ones
  const [newPropertiesToFill, setNewPropertiesToFill] = useState<string[]>([]); // Only visible properties
  const [newPropertyValues, setNewPropertyValues] = useState<any>({});
  const [loadingSchema, setLoadingSchema] = useState(false);
  const [newTemplateSchema, setNewTemplateSchema] = useState<any | null>(null);
  const [removedProperties, setRemovedProperties] = useState<string[]>([]);

  // Cache for current template to avoid refetching the same template repeatedly while selecting versions
  const currentTemplateRef = useRef<any | null>(null);

  // Invalidate cache if the resource's template name or current template version changes
  useEffect(() => {
    currentTemplateRef.current = null;
  }, [props.resource.templateName, props.resource.templateVersion]);

  const upgradeProps = {
    type: DialogType.normal,
    title: `Upgrade Template Version?`,
    closeButtonAriaLabel: "Close",
    subText: `Are you sure you want upgrade the template version of ${props.resource.properties.display_name} from version ${props.resource.templateVersion}?`,
  };

  const dialogStyles = { main: { maxWidth: 450 } };
  const modalProps = {
    titleAriaId: "labelId",
    subtitleAriaId: "subTextId",
    isBlocking: true,
    styles: dialogStyles,
  };

  // Template GET endpoints (templateGetPath) always use TRE API authentication,
  // even for UserResource templates, because they use paths like:
  // /workspace-service-templates/{name} (not /workspaces/{id}/...)
  const templateUsesWsAuth = false;

  // However, the actual resource instance upgrade operation (PATCH) uses workspace auth
  // for WorkspaceService and UserResource instances
  const instanceUsesWsAuth =
    props.resource.resourceType === ResourceType.WorkspaceService ||
    props.resource.resourceType === ResourceType.UserResource;

  // Fetch new template schema and identify new properties missing in current resource
  useEffect(() => {
    if (!selectedVersion) {
      setAllNewProperties([]);
      setNewPropertiesToFill([]);
      setNewPropertyValues({});
      setNewTemplateSchema(null);
      setRemovedProperties([]);
      return;
    }

    // Construct API paths for templates of specified resourceType
    let templateListPath;
    // Usually, the GET path would be `${templateGetPath}/${selectedTemplate}`, but there's an exception for user resources
    let templateGetPath;

    // let workspaceApplicationIdURI = undefined;
    switch (props.resource.resourceType) {
      case ResourceType.Workspace:
        templateListPath = ApiEndpoint.WorkspaceTemplates;
        templateGetPath = templateListPath;
        break;
      case ResourceType.WorkspaceService:
        templateListPath = ApiEndpoint.WorkspaceServiceTemplates;
        templateGetPath = templateListPath;
        break;
      case ResourceType.SharedService:
        templateListPath = ApiEndpoint.SharedServiceTemplates;
        templateGetPath = templateListPath;
        break;
      case ResourceType.UserResource:
        if (props.resource.properties.parentWorkspaceService) {
          // If we are upgrading a user resource, parent resource must have a workspaceId
          const workspaceId = (props.resource.properties.parentWorkspaceService as WorkspaceService)
            .workspaceId;
          templateListPath = `${ApiEndpoint.Workspaces}/${workspaceId}/${ApiEndpoint.WorkspaceServiceTemplates}/${props.resource.properties.parentWorkspaceService.templateName}/${ApiEndpoint.UserResourceTemplates}`;
          templateGetPath = `${ApiEndpoint.WorkspaceServiceTemplates}/${props.resource.properties.parentWorkspaceService.templateName}/${ApiEndpoint.UserResourceTemplates}`;
          // workspaceApplicationIdURI = props.resource.properties.parentWorkspaceService.workspaceApplicationIdURI;
          break;
        } else {
          throw Error(
            "Parent workspace service must be passed as prop when creating user resource.",
          );
        }
      default:
        throw Error("Unsupported resource type.");
    }

    const fetchNewTemplateSchema = async () => {
      setLoadingSchema(true);
      setApiError(null);
      try {
        let fetchUrl = "";

        fetchUrl = `${templateGetPath}/${props.resource.templateName}?version=${selectedVersion}`;

        const newTemplate = await apiCall(
          fetchUrl,
          HttpMethod.Get,
          templateUsesWsAuth ? workspaceCtx.workspaceApplicationIdURI : undefined,
          undefined,
          ResultType.JSON,
        );

        // Reuse cached current template if available to avoid redundant network calls
        let currentTemplate;
        if (currentTemplateRef.current) {
          currentTemplate = currentTemplateRef.current;
        } else {
          currentTemplate = await apiCall(
            `${templateGetPath}/${props.resource.templateName}?version=${props.resource.templateVersion}`,
            HttpMethod.Get,
            templateUsesWsAuth ? workspaceCtx.workspaceApplicationIdURI : undefined,
            undefined,
            ResultType.JSON,
          );
          currentTemplateRef.current = currentTemplate;
        }

        // Use full fetched schema from API
        setNewTemplateSchema(newTemplate);

        const newSchemaProps = newTemplate?.properties || {};
        const currentProps = currentTemplate?.properties || {};

        const newKeys = getAllPropertyKeys(newSchemaProps);
        const currentKeys = getAllPropertyKeys(currentProps);
        const newPropKeys = newKeys.filter((key) => {
          if (!currentKeys.includes(key)) {
            return true;
          }
          const propSchema = getSchemaProperty(newSchemaProps, key);
          const currentValue = getNestedValue(props.resource.properties, key);
          if (propSchema && propSchema.enum && currentValue !== undefined && !propSchema.enum.includes(currentValue)) {
            return true;
          }
          return false;
        });
        const removedPropsArray = currentKeys.filter((k) => !newKeys.includes(k));

        // Get properties defined in pipeline upgrade steps - these should NOT be sent by UI
        const pipelineProps = new Set<string>();
        if (newTemplate?.pipeline?.upgrade) {
          newTemplate.pipeline.upgrade.forEach((step: any) => {
            if (step.properties) {
              step.properties.forEach((prop: any) => {
                pipelineProps.add(prop.name);
              });
            }
          });
        }

        // Filter out properties that are in the pipeline - they will be substituted by the backend
        const newPropKeysWithoutPipeline = newPropKeys.filter((key) => {
          const topKey = key.split('.')[0];
          return !pipelineProps.has(topKey);
        });

        // Filter out properties that are hidden (tre-hidden) - they don't need user input
        const uiSchema = newTemplate?.uiSchema || {};
        const visibleNewPropKeys = newPropKeysWithoutPipeline.filter((key) => {
          const parts = key.split('.');
          let isHidden = false;
          let currentPath = '';
          for (const part of parts) {
            currentPath = currentPath ? `${currentPath}.${part}` : part;
            const propertyUiSchema = getNestedUiSchema(uiSchema, currentPath);
            const classNames = propertyUiSchema?.classNames || propertyUiSchema?.['ui:classNames'];
            if (classNames?.includes('tre-hidden')) {
              isHidden = true;
              break;
            }
          }
          return !isHidden;
        });

        setNewPropertiesToFill(visibleNewPropKeys);
        setRemovedProperties(removedPropsArray);

        // Include ALL new properties not in pipeline to be sent to API
        // This ensures hidden properties with defaults are correctly passed
        const newPropKeysToSend = newPropKeysWithoutPipeline;

        // Set allNewProperties to the filtered list (for schema building)
        setAllNewProperties(newPropKeysToSend);

        // prefill newPropertyValues with schema defaults (excluding pipeline properties)
        const initialValues: any = {};
        newPropKeysToSend.forEach((key) => {
          const topKey = key.split('.')[0];
          // If the top-level property already exists in the resource, copy it to avoid losing other sub-properties
          if (props.resource.properties && props.resource.properties[topKey] !== undefined) {
            if (!initialValues[topKey]) {
              initialValues[topKey] = JSON.parse(JSON.stringify(props.resource.properties[topKey]));
            }
          }

          const propSchema = getSchemaProperty(newTemplate?.properties, key);
          
          // Only set if a default value is defined in the schema
          if (propSchema && propSchema.default !== undefined) {
            setNestedValue(initialValues, key, propSchema.default);
          }
        });
        setNewPropertyValues(initialValues);
      } catch (err: any) {
        if (!err.userMessage) {
          err.userMessage = "Failed to fetch new template schema";
        }
        setApiError(err);
      } finally {
        setLoadingSchema(false);
      }
    };

    fetchNewTemplateSchema();
  }, [selectedVersion]);

  const upgradeCall = async () => {
    setRequestLoadingState(LoadingState.Loading);
    try {
      let body: any = { templateVersion: selectedVersion };

      body.properties = newPropertyValues;

      let op = await apiCall(
        props.resource.resourcePath,
        HttpMethod.Patch,
        instanceUsesWsAuth ? workspaceCtx.workspaceApplicationIdURI : undefined,
        body,
        ResultType.JSON,
        undefined,
        undefined,
        props.resource._etag,
      );
      dispatch(addUpdateOperation(op.operation));
      props.onDismiss();
    } catch (err: any) {
      if (!err.userMessage) {
        err.userMessage = "Failed to upgrade resource";
      }
      setApiError(err);
      setRequestLoadingState(LoadingState.Error);
    }
  };

  // Use buildReducedSchema to include all new properties (including hidden ones)
  // Hidden properties will be rendered but not shown due to tre-hidden CSS class
  const reducedSchemaProperties = newTemplateSchema
    ? buildReducedSchema(newTemplateSchema, allNewProperties)
    : null;

  // Extract any conditional blocks from full schema, filtered by all new properties
  const conditionalBlocks = newTemplateSchema ? extractConditionalBlocks(newTemplateSchema, allNewProperties) : {};

  // Compose final schema combining reduced properties with conditional blocks
  const finalSchema = reducedSchemaProperties
    ? { ...reducedSchemaProperties, ...conditionalBlocks }
    : null;

  // UI schema override: hide the form's submit button because we use external Upgrade button
  // start with existing UI order and classNames from full schema uiSchema
  const baseUiSchema = newTemplateSchema?.uiSchema || {};

  // Compose final uiSchema merging baseUiSchema with our overrides
  const uiSchema = {
    ...baseUiSchema,
    "ui:submitButtonOptions": { norender: true },
  };

  const onRenderOption = (option: any): JSX.Element => {
    return (
      <div>
        {option.data && option.data.icon && (
          <Icon
            style={{ marginRight: "8px" }}
            iconName={option.data.icon}
            aria-hidden="true"
            title={option.data.icon}
          />
        )}
        <span>{option.text}</span>
      </div>
    );
  };

  const convertToDropDownOptions = (upgrade: Array<AvailableUpgrade>) => {
    return upgrade.map((upgrade) => ({
      key: upgrade.version,
      text: upgrade.version,
      data: { icon: upgrade.forceUpdateRequired ? "Warning" : "" },
    }));
  };

  const getDropdownOptions = () => {
    const options = [];
    const nonMajorUpgrades = props.resource.availableUpgrades.filter(
      (upgrade) => !upgrade.forceUpdateRequired,
    );
    options.push(...convertToDropDownOptions(nonMajorUpgrades));
    return options;
  };

  return (
    <>
      <Dialog
        hidden={false}
        onDismiss={() => props.onDismiss()}
        dialogContentProps={upgradeProps}
        modalProps={modalProps}
      >
        {requestLoadingState === LoadingState.Ok && (
          <>
            <MessageBar messageBarType={MessageBarType.warning}>
              Upgrading the template version is irreversible.
            </MessageBar>

            {loadingSchema && <Spinner label="Loading new template schema..." />}
            {!loadingSchema && removedProperties.length > 0 && (
              <MessageBar messageBarType={MessageBarType.warning}>
                Warning: The following properties are no longer present in the template and will be removed: {removedProperties.join(', ')}
              </MessageBar>
            )}
            {!loadingSchema && allNewProperties.length > 0 && (
              <Stack tokens={{ childrenGap: 15 }}>
                {newPropertiesToFill.length > 0 && (
                  <MessageBar messageBarType={MessageBarType.info} styles={{ root: { marginBottom: 25 } }}>
                    You must specify values for new properties:
                  </MessageBar>
                )}

                {finalSchema && (
                  <Form
                    liveOmit={true}
                    omitExtraData={true}
                    schema={finalSchema}
                    formData={newPropertyValues}
                    uiSchema={uiSchema}
                    validator={validator}
                    onChange={(e) => setNewPropertyValues(e.formData)}
                  />
                )}
              </Stack>
            )}

            <DialogFooter>
              <Dropdown
                placeholder="Select Version"
                options={getDropdownOptions()}
                onRenderOption={onRenderOption}
                styles={{ dropdown: { width: 125 } }}
                onChange={(event, option) => {
                  option && setSelectedVersion(option.text);
                }}
                selectedKey={selectedVersion}
              />
              <PrimaryButton
                primaryDisabled={
                  !selectedVersion ||
                  (newPropertiesToFill.length > 0 &&
                    newPropertiesToFill.some((key) => {
                      const val = getNestedValue(newPropertyValues, key);

                      // Check if value is invalid enum (for both required and optional fields)
                      const propSchema = getSchemaProperty(newTemplateSchema?.properties, key);
                      if (propSchema && propSchema.enum && val !== undefined && val !== "" && !propSchema.enum.includes(val)) {
                        return true;
                      }

                      // Check if required field is empty
                      if (isPropertyRequiredInState(newTemplateSchema?.properties, newTemplateSchema?.required, key, newPropertyValues)) {
                        return val === "" || val === undefined;
                      }
                      return false;
                    }))
                }
                text="Upgrade"
                onClick={() => upgradeCall()}
              />
            </DialogFooter>
          </>
        )}
        {requestLoadingState === LoadingState.Loading && (
          <Spinner
            label="Sending request..."
            ariaLive="assertive"
            labelPosition="right"
          />
        )}
        {requestLoadingState === LoadingState.Error && (
          <ExceptionLayout e={apiError ?? ({} as APIError)} />
        )}
      </Dialog>
    </>
  );
};
