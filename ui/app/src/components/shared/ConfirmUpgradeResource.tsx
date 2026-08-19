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
import React, { useContext, useState, useEffect, useRef, useMemo } from "react";
import { AvailableUpgrade, Resource } from "../../models/resource";
import { UserResource } from "../../models/userResource";
import { ApiEndpoint } from "../../models/apiEndpoints";
import { WorkspaceService } from "../../models/workspaceService";
import { HttpMethod, ResultType, useAuthApiCall } from "../../hooks/useAuthApiCall";
import { WorkspaceContext } from "../../contexts/WorkspaceContext";
import { ResourceType } from "../../models/resourceType";
import { APIError } from "../../models/exceptions";
import { LoadingState } from "../../models/loadingState";
import { ExceptionLayout } from "./ExceptionLayout";
import { useAppDispatch } from "../../hooks/customReduxHooks";
import { addUpdateOperation } from "../shared/notifications/operationsSlice";
import Form from "@rjsf/fluent-ui";
import validator from "@rjsf/validator-ajv8";
import {
  getNestedValue,
  setNestedValue,
  clonePropertyValues,
  getSchemaProperty,
  getNestedUiSchema,
  isPropertyRequiredInState,
  mergePropertyValues,
  buildReducedSchema,
  extractConditionalBlocks,
  getAllPropertyKeysFromTemplate,
  getConditionalPropertyKeysForTriggers,
  isKeyActiveInTemplate,
} from "../../utils/schemaUpgradeUtils";

interface ConfirmUpgradeProps {
  resource: Resource;
  onDismiss: () => void;
  parentWorkspaceService?: WorkspaceService;
}

// Pure utility: prune ui:order in a uiSchema node to only reference properties present in the given schema node
const pruneUiSchemaOrder = (uiSchemaNode: any, schemaNode: any): any => {
  if (!uiSchemaNode || typeof uiSchemaNode !== "object") return uiSchemaNode;
  const result: any = { ...uiSchemaNode };

  const validPropNames = schemaNode && schemaNode.properties ? Object.keys(schemaNode.properties) : [];

  if (Array.isArray(result["ui:order"])) {
    const prunedOrder = result["ui:order"].filter((item: string) => item === "*" || validPropNames.includes(item));
    if (!prunedOrder.includes("*")) {
      prunedOrder.push("*");
    }
    result["ui:order"] = prunedOrder;
  }

  if (schemaNode && schemaNode.properties) {
    for (const key of Object.keys(schemaNode.properties)) {
      if (result[key] && typeof result[key] === "object") {
        result[key] = pruneUiSchemaOrder(result[key], schemaNode.properties[key]);
      }
    }
  }

  return result;
};

export const ConfirmUpgradeResource: React.FunctionComponent<ConfirmUpgradeProps> = (props: ConfirmUpgradeProps) => {
  const apiCall = useAuthApiCall();
  const [selectedVersion, setSelectedVersion] = useState("");
  const [apiError, setApiError] = useState<APIError | null>(null);
  const [requestLoadingState, setRequestLoadingState] = useState(LoadingState.Ok);
  const workspaceCtx = useContext(WorkspaceContext);
  const dispatch = useAppDispatch();

  const [allNewProperties, setAllNewProperties] = useState<string[]>([]); // All new properties including hidden ones
  const [newPropertiesToFill, setNewPropertiesToFill] = useState<string[]>([]); // Only visible properties
  const [newPropertyValues, setNewPropertyValues] = useState<Record<string, any>>({});
  const [formHasErrors, setFormHasErrors] = useState<boolean>(false);
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

  // However, the actual resource instance upgrade operation (PATCH) uses workspace auth
  // for WorkspaceService and UserResource instances
  const instanceUsesWsAuth =
    props.resource.resourceType === ResourceType.WorkspaceService ||
    props.resource.resourceType === ResourceType.UserResource;

  const extractNewPropertyValues = (formData: any, templateSchema: any, keys: string[]) => {
    const updatedNewVals: Record<string, any> = {};
    keys.forEach((key) => {
      if (isKeyActiveInTemplate(templateSchema, key, formData)) {
        const val = getNestedValue(formData, key);
        if (val !== undefined) {
          setNestedValue(updatedNewVals, key, val, formData);
        } else {
          const propSchema = getSchemaProperty(templateSchema, key);
          if (isPropertyRequiredInState(templateSchema, key, formData) && propSchema?.default !== undefined) {
            setNestedValue(updatedNewVals, key, propSchema.default, formData);
          }
        }
      }
    });
    return updatedNewVals;
  };

  // Fetch new template schema and identify new properties missing in current resource
  useEffect(() => {
    let didCancel = false;

    if (!selectedVersion) {
      setAllNewProperties([]);
      setNewPropertiesToFill([]);
      setNewPropertyValues({});
      setNewTemplateSchema(null);
      setRemovedProperties([]);
      return;
    }

    // Construct API path for templates of specified resourceType
    // Usually, the GET path would be `${templateGetPath}/${selectedTemplate}`, but there's an exception for user resources
    let templateGetPath;

    switch (props.resource.resourceType) {
      case ResourceType.Workspace:
        templateGetPath = ApiEndpoint.WorkspaceTemplates;
        break;
      case ResourceType.WorkspaceService:
        templateGetPath = ApiEndpoint.WorkspaceServiceTemplates;
        break;
      case ResourceType.SharedService:
        templateGetPath = ApiEndpoint.SharedServiceTemplates;
        break;
      case ResourceType.UserResource: {
        const ur = props.resource as UserResource;

        // Prefer explicit prop when provided
        let parentService: WorkspaceService | undefined = props.parentWorkspaceService;

        // Otherwise, try to read any embedded parentWorkspaceService in the resource properties
        if (!parentService && props.resource.properties?.parentWorkspaceService) {
          parentService = props.resource.properties.parentWorkspaceService as WorkspaceService;
        }

        if (parentService && parentService.templateName) {
          templateGetPath = `${ApiEndpoint.WorkspaceServiceTemplates}/${parentService.templateName}/${ApiEndpoint.UserResourceTemplates}`;
          break;
        }

        // If we don't have the full parent service but do have an ID, defer and fetch the parent service later
        if (!parentService && ur.parentWorkspaceServiceId) {
          if (workspaceCtx.workspace?.id) {
            // signal to fetch the parent workspace service inside fetchNewTemplateSchema
            templateGetPath = "";
            break;
          } else {
            const err = new APIError();
            err.userMessage =
              "Cannot resolve parent workspace service for this user resource because workspace context is missing.";
            err.status = 400;
            setApiError(err);
            setRequestLoadingState(LoadingState.Error);
            setLoadingSchema(false);
            return;
          }
        }

        // No parent information available at all -> report error to UI instead of throwing
        const err = new APIError();
        err.userMessage = "Parent workspace service information is missing for this user resource.";
        err.status = 400;
        setApiError(err);
        setRequestLoadingState(LoadingState.Error);
        setLoadingSchema(false);
        return;
      }
      default:
        // Report unsupported resource type to UI rather than throwing
        const err = new APIError();
        err.userMessage = `Unsupported resource type: ${props.resource.resourceType}`;
        err.status = 400;
        setApiError(err);
        setRequestLoadingState(LoadingState.Error);
        setLoadingSchema(false);
        return;
    }

    const fetchNewTemplateSchema = async () => {
      setLoadingSchema(true);
      setApiError(null);
      setRequestLoadingState(LoadingState.Ok);
      try {
        let activeTemplateGetPath = templateGetPath;
        if (!activeTemplateGetPath && props.resource.resourceType === ResourceType.UserResource) {
          const ur = props.resource as UserResource;
          if (ur.parentWorkspaceServiceId && workspaceCtx.workspace?.id) {
            const parentResponse = await apiCall(
              `${ApiEndpoint.Workspaces}/${workspaceCtx.workspace.id}/${ApiEndpoint.WorkspaceServices}/${ur.parentWorkspaceServiceId}`,
              HttpMethod.Get,
              workspaceCtx.workspaceApplicationIdURI,
            );
            if (didCancel) return;

            const parentService = parentResponse?.workspaceService as WorkspaceService;
            if (parentService && parentService.templateName) {
              activeTemplateGetPath = `${ApiEndpoint.WorkspaceServiceTemplates}/${parentService.templateName}/${ApiEndpoint.UserResourceTemplates}`;
            }
          }
        }

        if (!activeTemplateGetPath) {
          if (didCancel) return;
          const err = new APIError();
          err.userMessage = "Parent workspace service information is missing for this user resource.";
          err.status = 400;
          setApiError(err);
          setRequestLoadingState(LoadingState.Error);
          setLoadingSchema(false);
          return;
        }

        let fetchUrl = `${activeTemplateGetPath}/${props.resource.templateName}?version=${selectedVersion}`;

        const newTemplate = await apiCall(fetchUrl, HttpMethod.Get, undefined, undefined, ResultType.JSON);
        if (didCancel) return;

        // Reuse cached current template if available to avoid redundant network calls
        let currentTemplate;
        if (currentTemplateRef.current) {
          currentTemplate = currentTemplateRef.current;
        } else {
          currentTemplate = await apiCall(
            `${activeTemplateGetPath}/${props.resource.templateName}?version=${props.resource.templateVersion}`,
            HttpMethod.Get,
            undefined,
            undefined,
            ResultType.JSON,
          );
          if (didCancel) return;
          currentTemplateRef.current = currentTemplate;
        }

        if (didCancel) return;

        // Use full fetched schema from API
        setNewTemplateSchema(newTemplate);

        const newKeys = getAllPropertyKeysFromTemplate(newTemplate, props.resource.properties);
        const currentKeys = getAllPropertyKeysFromTemplate(currentTemplate, props.resource.properties);

        // Build a state with target-template defaults applied so that allOf branch conditions
        // introduced by the new template (e.g. a new selector with a default value) are
        // evaluated correctly when checking which properties become required on upgrade.
        const stateWithNewDefaults = clonePropertyValues(props.resource.properties);
        newKeys.forEach((key) => {
          if (getNestedValue(stateWithNewDefaults, key) === undefined) {
            const propSchema = getSchemaProperty(newTemplate, key);
            if (propSchema && propSchema.default !== undefined) {
              setNestedValue(stateWithNewDefaults, key, propSchema.default);
            }
          }
        });

        const newPropKeys = newKeys.filter((key) => {
          const currentValue = getNestedValue(props.resource.properties, key);
          if (!currentKeys.includes(key)) {
            return true;
          }
          if (currentValue === undefined && isPropertyRequiredInState(newTemplate, key, stateWithNewDefaults)) {
            return true;
          }
          const propSchema = getSchemaProperty(newTemplate, key);
          if (propSchema && propSchema.enum && currentValue !== undefined && !propSchema.enum.includes(currentValue)) {
            return true;
          }
          return false;
        });

        // Include conditional branch properties controlled by changed selectors. They may become
        // active after the user changes a selector value in the upgrade form.
        const conditionalPropertyKeys = getConditionalPropertyKeysForTriggers(newTemplate, newPropKeys);
        const newPropKeysWithConditionalProperties = [...new Set([...newPropKeys, ...conditionalPropertyKeys])];

        // Compute removedPropsArray based on property keys present in current resource instance that are no longer in new template
        const removedPropsArray = currentKeys.filter(
          (k) => !newKeys.includes(k) && getNestedValue(props.resource.properties, k) !== undefined,
        );

        // Get properties defined in pipeline upgrade steps - these should NOT be sent by UI
        const pipelineProps = new Set<string>();
        if (newTemplate?.pipeline?.upgrade) {
          newTemplate.pipeline.upgrade.forEach((step: any) => {
            if (step.stepId !== "main") {
              return;
            }
            if (step.properties) {
              step.properties.forEach((prop: any) => {
                pipelineProps.add(prop.name);
              });
            }
          });
        }

        // Filter out properties that are in the pipeline - they will be substituted by the backend
        const newPropKeysWithoutPipeline = newPropKeysWithConditionalProperties.filter((key) => {
          const topKey = key.split(".")[0];
          return !pipelineProps.has(topKey);
        });

        // Filter out properties that are hidden (tre-hidden) - they don't need user input unless they have an invalid enum value or are missing required properties
        const uiSchema = newTemplate?.uiSchema || {};
        const visibleNewPropKeys = newPropKeysWithoutPipeline.filter((key) => {
          const propSchema = getSchemaProperty(newTemplate, key);
          const currentValue = getNestedValue(props.resource.properties, key);
          const isEnumInvalid =
            propSchema &&
            Array.isArray(propSchema.enum) &&
            currentValue !== undefined &&
            !propSchema.enum.includes(currentValue);

          const isMissingRequired =
            currentValue === undefined && isPropertyRequiredInState(newTemplate, key, stateWithNewDefaults);

          if (isEnumInvalid || isMissingRequired) {
            return true;
          }

          const parts = key.split(".");
          let isHidden = false;
          let currentPath = "";
          for (const part of parts) {
            currentPath = currentPath ? `${currentPath}.${part}` : part;
            const propertyUiSchema = getNestedUiSchema(uiSchema, currentPath);
            const classNames = propertyUiSchema?.classNames || propertyUiSchema?.["ui:classNames"];
            if (classNames?.includes("tre-hidden")) {
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

        // prefill newPropertyValues with schema defaults for active branches only
        const initialCombinedState = clonePropertyValues(mergePropertyValues(props.resource.properties, {}));
        const initialValues: any = clonePropertyValues(props.resource.properties);
        newPropKeysToSend.forEach((key) => {
          if (!isKeyActiveInTemplate(newTemplate, key, initialCombinedState)) {
            return;
          }
          const propSchema = getSchemaProperty(newTemplate, key);
          const currentValue = getNestedValue(props.resource.properties, key);

          const isCurrentValueAllowed =
            currentValue !== undefined &&
            (!propSchema?.enum || (Array.isArray(propSchema.enum) && propSchema.enum.includes(currentValue)));

          if (isCurrentValueAllowed) {
            setNestedValue(initialValues, key, currentValue);
          } else if (propSchema && propSchema.default !== undefined) {
            setNestedValue(initialValues, key, propSchema.default);
            setNestedValue(initialCombinedState, key, propSchema.default);
          }
        });
        setNewPropertyValues(initialValues);
      } catch (err: any) {
        if (didCancel) return;
        if (!err.userMessage) {
          err.userMessage = "Failed to fetch new template schema";
        }
        setApiError(err);
        setRequestLoadingState(LoadingState.Error);
      } finally {
        if (!didCancel) {
          setLoadingSchema(false);
        }
      }
    };

    fetchNewTemplateSchema();

    return () => {
      didCancel = true;
    };
  }, [
    selectedVersion,
    props.resource.id,
    props.resource.resourceType,
    props.resource.templateName,
    props.resource.templateVersion,
    props.parentWorkspaceService?.id,
    props.parentWorkspaceService?.templateName,
    workspaceCtx.workspace?.id,
    workspaceCtx.workspaceApplicationIdURI,
    apiCall,
  ]);

  const upgradeCall = async () => {
    setRequestLoadingState(LoadingState.Loading);
    try {
      const mergedFormData = mergePropertyValues(props.resource.properties, newPropertyValues);
      const activePropertiesToPatch = extractNewPropertyValues(mergedFormData, newTemplateSchema, allNewProperties);

      let body: any = { templateVersion: selectedVersion, properties: activePropertiesToPatch };

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

  const combinedState = useMemo(
    () => mergePropertyValues(props.resource.properties, newPropertyValues),
    [props.resource.properties, newPropertyValues],
  );

  const isUpgradeDisabled = useMemo(() => {
    if (!selectedVersion || loadingSchema || formHasErrors) return true;
    if (newPropertiesToFill.length === 0) return false;

    return newPropertiesToFill.some((key) => {
      if (!isKeyActiveInTemplate(newTemplateSchema, key, combinedState)) {
        return false;
      }
      const valInState = getNestedValue(combinedState, key);
      const valInNew = getNestedValue(newPropertyValues, key);
      const propSchema = getSchemaProperty(newTemplateSchema, key);

      if (
        propSchema?.enum &&
        valInState !== undefined &&
        valInState !== null &&
        valInState !== "" &&
        !propSchema.enum.includes(valInState)
      ) {
        return true;
      }

      return (
        isPropertyRequiredInState(newTemplateSchema, key, combinedState) &&
        (valInNew === "" || valInNew === undefined || valInNew === null)
      );
    });
  }, [
    combinedState,
    formHasErrors,
    loadingSchema,
    newPropertiesToFill,
    newPropertyValues,
    newTemplateSchema,
    selectedVersion,
  ]);

  // Use buildReducedSchema to include all new properties (including hidden ones)
  // Hidden properties will be rendered but not shown due to tre-hidden CSS class
  const reducedSchemaProperties = newTemplateSchema ? buildReducedSchema(newTemplateSchema, allNewProperties) : null;

  // Extract any conditional blocks from full schema, filtered by all new properties
  const conditionalBlocks = newTemplateSchema ? extractConditionalBlocks(newTemplateSchema, allNewProperties) : {};

  // Compose final schema combining reduced properties with conditional blocks.
  // Allow unevaluated properties in this reduced form schema so existing resource properties
  // passed via formData are not flagged as invalid by AJV.
  const finalSchema = reducedSchemaProperties
    ? { ...reducedSchemaProperties, ...conditionalBlocks, unevaluatedProperties: true }
    : null;

  // UI schema override: hide the form's submit button because we use external Upgrade button
  // start with existing UI order and classNames from full schema uiSchema
  const baseUiSchema = newTemplateSchema?.uiSchema || {};

  // Strip tre-hidden for visible new properties so user can edit them if needed
  const sanitizedUiSchema = React.useMemo(() => {
    if (!baseUiSchema || !newPropertiesToFill.length) return baseUiSchema;
    const safeDeepClone = (obj: any): any => {
      if (obj === null || typeof obj !== "object") return obj;
      if (Array.isArray(obj)) return obj.map(safeDeepClone);
      const res: Record<string, any> = {};
      for (const key of Object.keys(obj)) {
        if (key === "__proto__" || key === "constructor" || key === "prototype") continue;
        res[key] = safeDeepClone(obj[key]);
      }
      return res;
    };
    const cloned = safeDeepClone(baseUiSchema);
    newPropertiesToFill.forEach((key) => {
      const parts = key.split(".");
      let current = cloned;
      for (let i = 0; i < parts.length; i++) {
        const part = parts[i];
        if (part === "__proto__" || part === "constructor" || part === "prototype") break;
        if (!current || typeof current !== "object" || !current[part]) break;
        if (typeof current[part].classNames === "string") {
          current[part].classNames = current[part].classNames.replace(/\btre-hidden\b/g, "").trim();
        }
        if (typeof current[part]["ui:classNames"] === "string") {
          current[part]["ui:classNames"] = current[part]["ui:classNames"].replace(/\btre-hidden\b/g, "").trim();
        }
        current = current[part];
      }
    });
    return cloned;
  }, [baseUiSchema, newPropertiesToFill]);

  // Compose final uiSchema merging sanitizedUiSchema with our overrides and pruning ui:order
  const uiSchema = useMemo(() => {
    const prunedUiSchema = finalSchema ? pruneUiSchemaOrder(sanitizedUiSchema, finalSchema) : sanitizedUiSchema;
    return {
      ...prunedUiSchema,
      "ui:submitButtonOptions": { norender: true },
    };
  }, [sanitizedUiSchema, finalSchema]);

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
    const nonMajorUpgrades = props.resource.availableUpgrades.filter((upgrade) => !upgrade.forceUpdateRequired);
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
                Warning: The following properties are no longer present in the template and will be removed:{" "}
                {removedProperties.join(", ")}
              </MessageBar>
            )}
            {!loadingSchema && allNewProperties.length > 0 && (
              <Stack tokens={{ childrenGap: 15 }}>
                {newPropertiesToFill.length > 0 && (
                  <MessageBar messageBarType={MessageBarType.info} styles={{ root: { marginBottom: 25 } }}>
                    Review values for new or changed properties:
                  </MessageBar>
                )}

                {finalSchema && (
                  <Form
                    liveValidate
                    liveOmit={false}
                    omitExtraData={false}
                    schema={finalSchema}
                    formData={combinedState}
                    uiSchema={uiSchema}
                    validator={validator}
                    onChange={(e) => {
                      const updatedNewVals = extractNewPropertyValues(e.formData, newTemplateSchema, allNewProperties);
                      setNewPropertyValues(updatedNewVals);
                      setFormHasErrors(Boolean(e.errors && e.errors.length > 0));
                    }}
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
                  if (option) {
                    setSelectedVersion(option.text);
                    setFormHasErrors(false);
                  }
                }}
                selectedKey={selectedVersion}
              />
              <PrimaryButton disabled={isUpgradeDisabled} text="Upgrade" onClick={() => upgradeCall()} />
            </DialogFooter>
          </>
        )}
        {requestLoadingState === LoadingState.Loading && (
          <Spinner label="Sending request..." ariaLive="assertive" labelPosition="right" />
        )}
        {requestLoadingState === LoadingState.Error && apiError && <ExceptionLayout e={apiError} />}
      </Dialog>
    </>
  );
};
