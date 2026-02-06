import { Spinner, SpinnerSize } from "@fluentui/react";
import { useEffect, useState } from "react";
import { LoadingState } from "../../../models/loadingState";
import {
  HttpMethod,
  ResultType,
  useAuthApiCall,
} from "../../../hooks/useAuthApiCall";
import Form from "@rjsf/fluent-ui";
import { Operation } from "../../../models/operation";
import { Resource } from "../../../models/resource";
import { ResourceType } from "../../../models/resourceType";
import { APIError } from "../../../models/exceptions";
import { ExceptionLayout } from "../ExceptionLayout";
import {
  ResourceTemplate,
  sanitiseTemplateForRJSF,
} from "../../../models/resourceTemplate";
import validator from "@rjsf/validator-ajv8";

interface ResourceFormProps {
  templateName: string;
  templatePath: string;
  resourcePath: string;
  updateResource?: Resource;
  onCreateResource: (operation: Operation) => void;
  workspaceApplicationIdURI?: string;
}

export const ResourceForm: React.FunctionComponent<ResourceFormProps> = (
  props: ResourceFormProps,
) => {
  const [template, setTemplate] = useState<any | null>(null);
  const [formData, setFormData] = useState({});
  const [loading, setLoading] = useState(LoadingState.Loading as LoadingState);
  const [sendingData, setSendingData] = useState(false);
  const apiCall = useAuthApiCall();
  const [apiError, setApiError] = useState({} as APIError);

  useEffect(() => {
    const getFullTemplate = async () => {
      try {
        // Get the full resource template containing the required parameters
        const templateResponse = (await apiCall(
          props.updateResource
            ? `${props.templatePath}?is_update=true&version=${props.updateResource.templateVersion}`
            : props.templatePath,
          HttpMethod.Get,
        )) as ResourceTemplate;

        // if it's an update, populate the form with the props that are available in the template
        if (props.updateResource) {
          setFormData(props.updateResource.properties);
        }

        const sanitisedTemplate = sanitiseTemplateForRJSF(templateResponse);
        setTemplate(sanitisedTemplate);
        setLoading(LoadingState.Ok);
      } catch (err: any) {
        err.userMessage = "Error retrieving resource template";
        setApiError(err);
        setLoading(LoadingState.Error);
      }
    };

    // Fetch full resource template only if not in state
    if (!template) {
      getFullTemplate();
    }
  }, [apiCall, props.templatePath, template, props.updateResource]);

  const removeReadOnlyProps = (data: any, template: ResourceTemplate): any => {
    // flatten all the nested properties from across the template into a basic array we can iterate easily
    let allProps = {} as any;

    const recurseTemplate = (templateFragment: any) => {
      Object.keys(templateFragment).forEach((key) => {
        if (key === "properties") {
          Object.keys(templateFragment[key]).forEach((prop) => {
            allProps[prop] = templateFragment[key][prop];
          });
        }
        if (typeof templateFragment[key] === "object" && key !== "if") {
          recurseTemplate(templateFragment[key]);
        }
      });
    };

    recurseTemplate(template);

    // iterate the data payload
    for (let prop in data) {
      // if the prop isn't in the template, or it's readOnly, delete it
      if (!allProps[prop] || allProps[prop].readOnly === true) {
        delete data[prop];
      }
    }

    return data;
  };

  const createUpdateResource = async (formData: any) => {
    const data = removeReadOnlyProps(formData, template);
    console.log("parsed payload to send", data);

    setSendingData(true);
    let response;
    try {
      if (props.updateResource) {
        const wsAuth =
          props.updateResource.resourceType === ResourceType.WorkspaceService ||
          props.updateResource.resourceType === ResourceType.UserResource;
        response = await apiCall(
          props.updateResource.resourcePath,
          HttpMethod.Patch,
          wsAuth ? props.workspaceApplicationIdURI : undefined,
          { properties: data },
          ResultType.JSON,
          undefined,
          undefined,
          props.updateResource._etag,
        );
      } else {
        const resource = { templateName: props.templateName, properties: data };
        response = await apiCall(
          props.resourcePath,
          HttpMethod.Post,
          props.workspaceApplicationIdURI,
          resource,
          ResultType.JSON,
        );
      }

      setSendingData(false);
      props.onCreateResource(response.operation);
    } catch (err: any) {
      err.userMessage = "Error sending create / update request";
      setApiError(err);
      setLoading(LoadingState.Error);
      setSendingData(false);
    }
  };

  // use the supplied uiSchema or create a blank one, and set the overview field to textarea manually.
  const uiSchema = (template && template.uiSchema) || {};
  uiSchema.overview = {
    ...uiSchema.overview,
    "ui:widget": "textarea",
  };

  // if no specific order has been set, set a generic one with the primary fields at the top
  if (!uiSchema["ui:order"] || uiSchema["ui:order"].length === 0) {
    uiSchema["ui:order"] = ["display_name", "description", "overview", "*"];
  }

  switch (loading) {
    case LoadingState.Ok:
      return (
        template && (
          <div style={{ marginTop: 20 }}>
            {sendingData ? (
              <Spinner
                label="Sending request"
                ariaLive="assertive"
                labelPosition="bottom"
                size={SpinnerSize.large}
              />
            ) : (
              <Form
                omitExtraData={true}
                schema={template}
                formData={formData}
                uiSchema={uiSchema}
                validator={validator}
                onSubmit={(e: any) => createUpdateResource(e.formData)}
              />
            )}
          </div>
        )
      );
    case LoadingState.Error:
      return <ExceptionLayout e={apiError} />;
    case LoadingState.Error:
      return <ExceptionLayout e={apiError} />;
    default:
      return (
        <div style={{ marginTop: 20 }}>
          <Spinner
            label="Loading template"
            ariaLive="assertive"
            labelPosition="top"
            size={SpinnerSize.large}
          />
        </div>
      );
  }
};
