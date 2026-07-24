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
  getSchemaProperty,
  getNestedUiSchema,
  isPropertyRequiredInState,
  buildReducedSchema,
  extractConditionalBlocks,
  getAllPropertyKeysFromTemplate,
  getTopLevelKeysFromTemplate,
} from "../../utils/schemaUpgradeUtils";

interface ConfirmUpgradeProps {
  resource: Resource;
  onDismiss: () => void;
  parentWorkspaceService?: WorkspaceService;
}

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
      case ResourceType.UserResource: {
        const ur = props.resource as UserResource;
        const parentService =
          props.parentWorkspaceService || (props.resource.properties?.parentWorkspaceService as WorkspaceService);

        if (parentService && parentService.templateName) {
          const workspaceId = parentService.workspaceId || workspaceCtx.workspace?.id;
          templateListPath = `${ApiEndpoint.Workspaces}/${workspaceId}/${ApiEndpoint.WorkspaceServiceTemplates}/${parentService.templateName}/${ApiEndpoint.UserResourceTemplates}`;
          templateGetPath = `${ApiEndpoint.WorkspaceServiceTemplates}/${parentService.templateName}/${ApiEndpoint.UserResourceTemplates}`;
          break;
        } else if (ur.parentWorkspaceServiceId && workspaceCtx.workspace?.id) {
          // Fall back to fetching parent workspace service via API inside fetchNewTemplateSchema if needed
          templateListPath = "";
          templateGetPath = "";
          break;
        } else {
          const err = new APIError();
          err.userMessage = "Parent workspace service information is missing for this user resource.";
          err.status = 400;
          setApiError(err);
          return;
        }
      }
      default:
        throw Error("Unsupported resource type.");
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
            const parentService = parentResponse?.workspaceService as WorkspaceService;
            if (parentService && parentService.templateName) {
              activeTemplateGetPath = `${ApiEndpoint.WorkspaceServiceTemplates}/${parentService.templateName}/${ApiEndpoint.UserResourceTemplates}`;
            }
          }
        }

        if (!activeTemplateGetPath) {
          const err = new APIError();
          err.userMessage = "Parent workspace service information is missing for this user resource.";
          err.status = 400;
          setApiError(err);
          setRequestLoadingState(LoadingState.Error);
          setLoadingSchema(false);
          return;
        }

        let fetchUrl = `${activeTemplateGetPath}/${props.resource.templateName}?version=${selectedVersion}`;

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
            `${activeTemplateGetPath}/${props.resource.templateName}?version=${props.resource.templateVersion}`,
            HttpMethod.Get,
            templateUsesWsAuth ? workspaceCtx.workspaceApplicationIdURI : undefined,
            undefined,
            ResultType.JSON,
          );
          currentTemplateRef.current = currentTemplate;
        }

        // Use full fetched schema from API
        setNewTemplateSchema(newTemplate);

        const newKeys = getAllPropertyKeysFromTemplate(newTemplate);
        const currentKeys = getAllPropertyKeysFromTemplate(currentTemplate);
        const newPropKeys = newKeys.filter((key) => {
          if (!currentKeys.includes(key)) {
            return true;
          }
          const propSchema = getSchemaProperty(newTemplate, key);
          const currentValue = getNestedValue(props.resource.properties, key);
          if (propSchema && propSchema.enum && currentValue !== undefined && !propSchema.enum.includes(currentValue)) {
            return true;
          }
          return false;
        });

        // Compute removedPropsArray based only on top-level keys
        const currentTopKeys = getTopLevelKeysFromTemplate(currentTemplate);
        const newTopKeys = getTopLevelKeysFromTemplate(newTemplate);
        const removedPropsArray = currentTopKeys.filter((k) => !newTopKeys.includes(k));

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
          const topKey = key.split(".")[0];
          return !pipelineProps.has(topKey);
        });

        // Filter out properties that are hidden (tre-hidden) - they don't need user input
        const uiSchema = newTemplate?.uiSchema || {};
        const visibleNewPropKeys = newPropKeysWithoutPipeline.filter((key) => {
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

        // prefill newPropertyValues with schema defaults (excluding pipeline properties)
        const initialValues: any = {};
        newPropKeysToSend.forEach((key) => {
          const topKey = key.split(".")[0];
          // If the top-level property already exists in the resource, copy it to avoid losing other sub-properties
          if (props.resource.properties && props.resource.properties[topKey] !== undefined) {
            if (!initialValues[topKey]) {
              initialValues[topKey] = JSON.parse(JSON.stringify(props.resource.properties[topKey]));
            }
          }

          const propSchema = getSchemaProperty(newTemplate, key);

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
        setRequestLoadingState(LoadingState.Error);
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
  const reducedSchemaProperties = newTemplateSchema ? buildReducedSchema(newTemplateSchema, allNewProperties) : null;

  // Extract any conditional blocks from full schema, filtered by all new properties
  const conditionalBlocks = newTemplateSchema ? extractConditionalBlocks(newTemplateSchema, allNewProperties) : {};

  // Compose final schema combining reduced properties with conditional blocks
  const finalSchema = reducedSchemaProperties ? { ...reducedSchemaProperties, ...conditionalBlocks } : null;

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
                      const propSchema = getSchemaProperty(newTemplateSchema, key);
                      if (
                        propSchema &&
                        propSchema.enum &&
                        val !== undefined &&
                        val !== "" &&
                        !propSchema.enum.includes(val)
                      ) {
                        return true;
                      }

                      // Check if required field is empty
                      if (isPropertyRequiredInState(newTemplateSchema, key, newPropertyValues)) {
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
          <Spinner label="Sending request..." ariaLive="assertive" labelPosition="right" />
        )}
        {requestLoadingState === LoadingState.Error && <ExceptionLayout e={apiError ?? ({} as APIError)} />}
      </Dialog>
    </>
  );
};
