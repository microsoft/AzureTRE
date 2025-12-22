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

  const [newPropertiesToFill, setNewPropertiesToFill] = useState<string[]>([]);
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

  const wsAuth =
    props.resource.resourceType === ResourceType.WorkspaceService ||
    props.resource.resourceType === ResourceType.UserResource;

  // Fetch new template schema and identify new properties missing in current resource
  useEffect(() => {
    if (!selectedVersion) {
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
          props.resource.resourceType === ResourceType.UserResource ? workspaceCtx.workspaceApplicationIdURI : undefined,
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
            props.resource.resourceType === ResourceType.UserResource ? workspaceCtx.workspaceApplicationIdURI : undefined,
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

        const newPropKeys = newKeys.filter((k) => !currentKeys.includes(k));
        const removedPropsArray = currentKeys.filter((k) => !newKeys.includes(k));

        setNewPropertiesToFill(newPropKeys);
        setRemovedProperties(removedPropsArray);

        // prefill newPropertyValues with schema defaults or empty string
        setNewPropertyValues(
          newPropKeys.reduce((acc, key) => {
            // Get top-level portion of the key
            const topKey = key.split('.')[0];
            const defaultValue = newTemplate?.properties?.[topKey]?.default;
            acc[key] = defaultValue !== undefined ? defaultValue : '';
            return acc;
          }, {} as any),
        );
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
        wsAuth ? workspaceCtx.workspaceApplicationIdURI : undefined,
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

  // Use buildReducedSchema to include only new properties
  const reducedSchemaProperties = newTemplateSchema
    ? buildReducedSchema(newTemplateSchema, newPropertiesToFill)
    : null;

  // Extract any conditional blocks from full schema, filtered by new properties
  const conditionalBlocks = newTemplateSchema ? extractConditionalBlocks(newTemplateSchema, newPropertiesToFill) : {};

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
            {!loadingSchema && newPropertiesToFill.length > 0 && (
              <Stack tokens={{ childrenGap: 15 }}>
                <MessageBar messageBarType={MessageBarType.info} styles={{ root: { marginBottom: 25 } }}>
                  You must specify values for new properties:
                </MessageBar>

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
                    Object.values(newPropertyValues).some(
                      (v) => v === "" || v === undefined,
                    ))
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
